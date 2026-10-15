import logging
from collections import defaultdict

from hyperapp.boot.resource.workspace import Workspace, load_file_tree

from .services import (
    load_resources,
    )
from .code.transport import LocalEndpoint
from .code.selectors import StopSignal
from .code.path import Path
from .code.module import ModuleType, Module
from .code.target_set import TargetSet
from .code.target.import_target import ImportTarget
from .code.target.module import CompiledModuleTarget
from .data.worker import config as worker_config

log = logging.getLogger(__name__)


AUTO_GEN_LINE = '# Automatically generated file. Do not edit.'

DYN_EXT = '.dyn.py'
RESOURCES_EXT = '.resources.yaml'

RESULT_TIMEOUT_SEC = 10


def compile_resources(
        generate_rsa_identity,
        subprocess_workers_running,
        transport,
        message_creg,
        selectors,
        job_pool,
        workspace_path,
        ):
    master_identity = generate_rsa_identity(fast=True)
    transport.add_endpoint(master_identity.peer, LocalEndpoint(message_creg, master_identity))
    log.info("master identity: %s", master_identity)
    with subprocess_workers_running(
            master_identity, worker_config, 'sample', count=2, timeout_sec=5, start_timeout_sec=5) as workers:
        log.info("workers are running: %s", workers.peers)
        _compile(transport, selectors, job_pool, master_identity, workers, workspace_path)
    log.info("workers are finished")


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
    # others are compiled (including lone dyn modules).
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
    for module in modules:
        if module.type != ModuleType.COMPILED:
            continue
        module.import_tgt = ImportTarget.ensure(targets, module.path, module.source)
        module.module_tgt = CompiledModuleTarget.ensure(targets, module.path)


def _run(transport, selectors, job_pool, master_identity, workers, targets):
    stop_signal = StopSignal()
    with job_pool.running(master_identity, stop_signal, workers):
        with selectors.registered(stop_signal):
            for tgt in targets.enum_runnable():
                job_pool.start_job(tgt)
            if job_pool.pending:
                selectors.run(RESULT_TIMEOUT_SEC)
        log.info("%d import jobs are finished", len(job_pool.completed))


def _compile(transport, selectors, job_pool, master_identity, workers, workspace_path):
    log.info("Loading workspace: %s", workspace_path)
    workspace = Workspace.from_yaml_file(workspace_path)
    project_to_tree = workspace.load_file_tree()
    modules = _collect_modules(project_to_tree)
    targets = TargetSet(modules)
    _create_targets(modules, targets)
    compiled_count = sum(1 for m in modules if m.type == ModuleType.COMPILED)
    log.info("%d modules, %d compiled", len(modules), compiled_count)
    resources, sources = load_resources(workspace.projects, project_to_tree)
    log.info("loaded %d resources, %d sources", len(resources), len(sources))
    log.info("%d targets", len(targets))
    _run(transport, selectors, job_pool, master_identity, workers, targets)
