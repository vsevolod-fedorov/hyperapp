import logging
from collections import defaultdict
from dataclasses import dataclass

from . import htypes
from .services import (
    load_resources,
    mosaic,
    )
from .code.transport import LocalEndpoint
from .code.path import Path
from .code.module import MissingModuleSource, ModuleType, Module
from .code.target_set import TargetSet
from .code.target.import_target import ImportAliasTarget, ImportTarget, ProjectImportsTarget
from .code.target.module import ManualModuleTarget
from .code.target.project import AllTarget
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
    errors: dict  # Target name -> own error and any cycle diagnostics, separated by newlines.
    cycles: list  # Dependency cycles, as (target name list, first one repeated last; hint or None) tuples.
    constructors: dict  # Provider Path -> concrete constructor pieces accepted by successful results.

    @property
    def succeeded(self):
        return self.target_states[AllTarget.name] == TargetState.RESOLVED


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
        additional_worker_configs=(),
        ):
    modules = _collect_modules(project_to_tree)
    effective_worker_config = worker_config
    if additional_worker_configs:
        # Later pieces override earlier ones through the same service config controllers as worker boot uses.
        effective_worker_config = htypes.system.system_config(
            services=tuple(
                rec
                for config in (worker_config, *additional_worker_configs)
                for rec in config.services
                ),
            )
    master_identity = generate_rsa_identity(fast=True)
    transport.add_endpoint(master_identity.peer, LocalEndpoint(message_creg, master_identity))
    log.info("master identity: %s", master_identity)
    with subprocess_workers_running(
            master_identity, effective_worker_config, 'sample',
            count=worker_count, timeout_sec=5, start_timeout_sec=5) as workers:
        log.info("workers are running: %s", workers.peers)
        result = _compile(
            transport, selectors, job_pool, name_resources, dump_resource_modules,
            master_identity, workers, projects, project_to_tree, modules)
    log.info("workers are finished")
    return result


def _collect_modules(project_to_tree):
    modules = []
    for project, tree in project_to_tree.items():
        module_paths = set()
        for path in tree:
            name = path[-1]
            if name.endswith(DYN_EXT):
                module_paths.add((*path[:-1], name[:-len(DYN_EXT)]))
            elif name.endswith(RESOURCES_EXT):
                module_paths.add((*path[:-1], name[:-len(RESOURCES_EXT)]))
        for path in sorted(module_paths):
            resources_path = (*path[:-1], path[-1] + RESOURCES_EXT)
            resources = tree.get(resources_path)
            if resources is not None and not resources.startswith(AUTO_GEN_LINE.encode()):
                modules.append(Module(ModuleType.MANUAL, Path(project, path)))
                continue
            dyn_path = (*path[:-1], path[-1] + DYN_EXT)
            if dyn_path not in tree:
                raise MissingModuleSource(
                    f"Generated file {project}:{'/'.join(resources_path)} has no source {'/'.join(dyn_path)}")
            modules.append(Module(ModuleType.DYNAMIC, Path(project, path), tree[dyn_path].decode()))
    return modules


# resources: loaded ones, name tuple -> piece. Manual modules are imported by them.
def _create_targets(modules, targets, resources):
    for module in modules:
        if module.type == ModuleType.MANUAL:
            _create_manual_target(module, targets, resources)
            continue
        module.import_tgt = ImportTarget.ensure(targets, module)
        module.import_alias_tgt = ImportAliasTarget.ensure(targets, module.path)
        module.project_imports_tgt = ProjectImportsTarget.ensure(targets, module.path.project)
        module.project_imports_tgt.add_module(module)


# Manual module without module resource, like a lone config one, gets no target: it can not be imported.
def _create_manual_target(module, targets, resources):
    path = module.path
    try:
        piece = resources[path.project, path.path, f'{path.path[-1]}.module']
    except KeyError:
        return
    module.module_tgt = ManualModuleTarget(path, piece)
    targets.add(path.project, module.module_tgt)


def _run(transport, selectors, job_pool, master_identity, workers, targets, goal):
    with job_pool.running(master_identity, workers):
        while True:
            for tgt in targets.enum_runnable(goal):
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


# A cycle is one diagnostic, but each member needs it when inspected on its own.
def _target_errors(targets, cycles):
    messages = defaultdict(list)
    for tgt in targets:
        if error := tgt.error:
            messages[tgt.name].append(error)
    for names, hint in cycles:
        message = f"Dependency cycle: {' -> '.join(names)}"
        if hint:
            message += f". {hint}"
        log.error("%s", message)
        for name in names[:-1]:  # The repeated first name closes the path.
            messages[name].append(message)
    return {name: '\n'.join(lines) for name, lines in messages.items()}


def _compile(
        transport, selectors, job_pool, name_resources, dump_resource_modules,
        master_identity, workers, projects, project_to_tree, modules):
    resources, sources = load_resources(projects, project_to_tree)
    log.info("loaded %d resources, %d sources", len(resources), len(sources))
    targets = TargetSet(projects, modules, resources)
    _create_targets(modules, targets, resources)
    dynamic_count = sum(1 for m in modules if m.type == ModuleType.DYNAMIC)
    log.info("%d modules, %d dynamic", len(modules), dynamic_count)
    log.info("%d targets", len(targets))
    _run(transport, selectors, job_pool, master_identity, workers, targets, targets.all_tgt)
    _log_targets(targets)
    _log_projects(targets.project_tgts)
    resource_locations = _resource_locations(targets.project_tgts)
    target_states = {tgt.name: tgt.state for tgt in targets}
    cycles = [([tgt.name for tgt in cycle], _cycle_hint(cycle)) for cycle in targets.cycles]
    errors = _target_errors(targets, cycles)
    piece_to_name = name_resources(resources, resource_locations)
    _log_names(piece_to_name, resource_locations)
    return CompileResult(
        resource_tree=_resource_tree(dump_resource_modules, projects, piece_to_name, resource_locations),
        target_states=target_states,
        errors=errors,
        cycles=cycles,
        constructors=targets.constructors.pieces,
        )
