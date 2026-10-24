import logging
from collections import defaultdict
from dataclasses import dataclass

from .services import (
    load_resources,
    mosaic,
    )
from .code.transport import LocalEndpoint
from .code.path import Path
from .code.module import ModuleType, Module
from .code.target_set import TargetSet
from .code.target.import_target import ImportAliasTarget, ImportTarget, ProjectImportsTarget
from .code.target.module import CompiledModuleTarget
from .code.target.project import ProjectTarget
from .code.target.state import TargetState
from .code.target.test import TestModuleTarget
from .data.worker import config as worker_config

log = logging.getLogger(__name__)


AUTO_GEN_LINE = '# Automatically generated file. Do not edit.'

DYN_EXT = '.dyn.py'
RESOURCES_EXT = '.resources.yaml'

RESULT_TIMEOUT_SEC = 10


@dataclass
class CompileResult:
    resource_tree: dict  # Generated files: project name -> file path tuple -> bytes.
    target_states: dict  # Target name -> TargetState.
    errors: dict  # Target name -> error, for targets failed by themselves, not by their deps.
    cycles: list  # Dependency cycles, as (target name list, first one repeated last; hint or None) tuples.


# Compile resources of workspace projects.
# project_to_tree: project name -> file path tuple -> bytes, the sources.
# worker_count: subprocess workers running jobs. It decides which jobs share a worker, and so its caches.
# Returns CompileResult.
def compile_resources(
        generate_rsa_identity,
        subprocess_workers_running,
        transport,
        message_creg,
        selectors,
        job_pool,
        name_resources,
        dump_resource_modules,
        projects,
        project_to_tree,
        worker_count,
        ):
    master_identity = generate_rsa_identity(fast=True)
    transport.add_endpoint(master_identity.peer, LocalEndpoint(message_creg, master_identity))
    log.info("master identity: %s", master_identity)
    with subprocess_workers_running(
            master_identity, worker_config, 'sample',
            count=worker_count, timeout_sec=5, start_timeout_sec=5) as workers:
        log.info("workers are running: %s", workers.peers)
        result = _compile(
            transport, selectors, job_pool, name_resources, dump_resource_modules,
            master_identity, workers, projects, project_to_tree)
    log.info("workers are finished")
    return result


def _collect_modules(project_to_tree):
    module_paths = defaultdict(set)  # project -> paths
    for project, tree in project_to_tree.items():
        for path, bytes in tree.items():
            name = path[-1]
            if name.endswith(DYN_EXT):
                module_paths[project].add((*path[:-1], name[:-len(DYN_EXT)]))
            if name.endswith(RESOURCES_EXT):
                module_paths[project].add((*path[:-1], name[:-len(RESOURCES_EXT)]))
    modules = []
    # Modules having resources (or lone resources) without auto-get line are manual,
    # others are compiled (including lone dyn modules). Some of compiled ones turn out to be tests when imported.
    for project, path_set in module_paths.items():
        for path in sorted(path_set):
            resources_path = (*path[:-1], path[-1] + RESOURCES_EXT)
            try:
                resources_text = project_to_tree[project][resources_path]
            except KeyError:
                pass
            else:
                if not resources_text.decode().startswith(AUTO_GEN_LINE):
                    modules.append(Module(ModuleType.MANUAL, Path(project, path)))
                    continue
            dyn_path = (*path[:-1], path[-1] + DYN_EXT)
            source = project_to_tree[project][dyn_path].decode()
            modules.append(Module(ModuleType.COMPILED, Path(project, path), source))
    return modules


def _create_targets(modules, targets):
    project_names = set()
    for module in modules:
        if module.type != ModuleType.COMPILED:
            continue
        module.module_tgt = CompiledModuleTarget(targets, module.path, module.source)
        module.import_tgt = ImportTarget.ensure(targets, module.path, module.source, module.module_tgt)
        module.import_alias_tgt = ImportAliasTarget.ensure(targets, module.path)
        # First imports decide which modules are tests, and what they test: compiled modules wait for them all,
        # and fail with them.
        ProjectImportsTarget.ensure(targets, module.path.project).add_dep(module.import_tgt)
        project_names.add(module.path.project)
    return [ProjectTarget.ensure(targets, name) for name in sorted(project_names)]


def _run(transport, selectors, job_pool, master_identity, workers, targets):
    with job_pool.running(master_identity, workers):
        while True:
            for tgt in targets.enum_runnable():
                job_pool.start_job(tgt)
            if not job_pool.pending:
                break
            if not selectors.run_once(RESULT_TIMEOUT_SEC):
                log.warning("Timed out waiting for job results")
                break
        log.info("%d import jobs are finished", len(job_pool.completed))
    log.info(
        "%d/%d targets resolved, %d failed",
        sum(1 for t in targets if t.state == TargetState.RESOLVED),
        len(targets),
        sum(1 for t in targets if t.state == TargetState.FAILED),
        )


def _target_state(tgt):
    return tgt.state.name.lower()


def _log_targets(targets):
    for tgt in sorted(targets, key=lambda t: t.name):
        log.info("Target %s: %s", tgt.name, _target_state(tgt))
        if tgt.state == TargetState.RESOLVED and tgt.result:
            log.info("  result: %s %s", mosaic.put(tgt.result), tgt.result)
        for dep in sorted(tgt.deps, key=lambda t: t.name):
            log.info("  dep %s: %s", dep.name, _target_state(dep))


def _log_projects(project_tgts):
    for tgt in project_tgts:
        log.info("Project %s: %s", tgt.name, _target_state(tgt))
        if tgt.state != TargetState.RESOLVED:
            continue
        for path, piece in sorted(tgt.resources.items(), key=lambda item: str(item[0])):
            log.info("  resource %s: %s %s", path, mosaic.put(piece), piece)


def _resource_locations(project_tgts):
    return {
        (path.project, path.path): piece
        for tgt in project_tgts
        if tgt.state == TargetState.RESOLVED
        for path, piece in tgt.resources.items()
        }


def _log_names(piece_to_name, resource_locations):
    for piece, (project_name, path, name) in sorted(piece_to_name.items(), key=lambda item: item[1]):
        if (project_name, path) in resource_locations:
            log.info("Named %s:%s:%s: %s %s", project_name, '/'.join(path), name, mosaic.put(piece), piece)


def _resource_tree(dump_resource_modules, projects, piece_to_name, resource_locations):
    location_to_text = dump_resource_modules(projects, piece_to_name, resource_locations)
    project_to_tree = defaultdict(dict)
    for (project_name, path), text in sorted(location_to_text.items()):
        file_path = (*path[:-1], path[-1] + RESOURCES_EXT)
        project_to_tree[project_name][file_path] = f'{AUTO_GEN_LINE}\n\n{text}'.encode()
    return dict(project_to_tree)


# Test modules know why tests got into a cycle.
def _cycle_hint(cycle):
    for tgt in cycle[:-1]:
        if isinstance(tgt, TestModuleTarget):
            if hint := tgt.cycle_hint(cycle):
                return hint
    return None


def _compile(
        transport, selectors, job_pool, name_resources, dump_resource_modules,
        master_identity, workers, projects, project_to_tree):
    modules = _collect_modules(project_to_tree)
    targets = TargetSet(projects, modules)
    project_tgts = _create_targets(modules, targets)
    compiled_count = sum(1 for m in modules if m.type == ModuleType.COMPILED)
    log.info("%d modules, %d compiled", len(modules), compiled_count)
    resources, sources = load_resources(projects, project_to_tree)
    log.info("loaded %d resources, %d sources", len(resources), len(sources))
    log.info("%d targets", len(targets))
    _run(transport, selectors, job_pool, master_identity, workers, targets)
    _log_targets(targets)
    _log_projects(project_tgts)
    resource_locations = _resource_locations(project_tgts)
    target_states = {tgt.name: tgt.state for tgt in targets}
    errors = {tgt.name: tgt.error for tgt in targets if tgt.error}
    cycles = [([tgt.name for tgt in cycle], _cycle_hint(cycle)) for cycle in targets.cycles]
    for names, hint in cycles:
        log.error("Dependency cycle: %s%s", " -> ".join(names), f". {hint}" if hint else "")
    piece_to_name = name_resources(resources, resource_locations)
    _log_names(piece_to_name, resource_locations)
    return CompileResult(
        resource_tree=_resource_tree(dump_resource_modules, projects, piece_to_name, resource_locations),
        target_states=target_states,
        errors=errors,
        cycles=cycles,
        )
