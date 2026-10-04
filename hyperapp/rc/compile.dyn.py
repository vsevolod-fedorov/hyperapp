import logging
from collections import defaultdict

from hyperapp.boot.resource.workspace import Workspace, load_file_tree

from .services import (
    load_resources,
    )
from .code.module import Module
from .code.transport import LocalEndpoint
from .code.path import Path
from .code.import_target import ImportTarget
from .data.worker import config as worker_config

log = logging.getLogger(__name__)


AUTO_GEN_LINE = '# Automatically generated file. Do not edit.'

DYN_EXT = '.dyn.py'
RESOURCES_EXT = '.resources.yaml'


def compile_resources(
        generate_rsa_identity,
        subprocess_workers_running,
        transport,
        message_creg,
        workspace_path,
        ):
    master_identity = generate_rsa_identity(fast=True)
    transport.add_endpoint(master_identity.peer, LocalEndpoint(message_creg, master_identity))
    log.info("master identity: %s", master_identity)
    with subprocess_workers_running(
            master_identity, worker_config, 'sample', count=2, timeout_sec=5, start_timeout_sec=5) as workers:
        log.info("workers are running: %s", workers.peers)
        _compile(transport, master_identity, workers, workspace_path)
    log.info("workers are finished")


def _collect_modules(project_to_tree):
    modules = defaultdict(set)  # project -> paths
    for project, tree in project_to_tree.items():
        for path, bytes in tree.items():
            name = path[-1]
            if name.endswith(DYN_EXT):
                modules[project].add((*path[:-1], name[:-len(DYN_EXT)]))
            if name.endswith(RESOURCES_EXT):
                modules[project].add((*path[:-1], name[:-len(RESOURCES_EXT)]))
    compiled = []  # Path list
    manual = []  # Path list
    # Modules having resources (or lone resources) without auto-get line are manual,
    # others are compiled (including lone dyn modules).
    for project, path_set in modules.items():
        for path in sorted(path_set):
            resources_path = (*path[:-1], path[-1] + RESOURCES_EXT)
            try:
                resources_text = project_to_tree[project][resources_path]
            except KeyError:
                pass
            else:
                if not resources_text.decode().startswith(AUTO_GEN_LINE):
                    manual.append(Path(project, path))
                    continue
            compiled.append(Path(project, path))
    return (manual, compiled)


def _create_targets(compiled_modules, project_to_tree):
    targets = []
    for path in compiled_modules:
        dyn_path = (*path.path[:-1], path.path[-1] + DYN_EXT)
        source = project_to_tree[path.project][dyn_path].decode()
        targets.append(ImportTarget(path, source))
    return targets


def _start_job(transport, master_identity, workers, job):
    log.info("Start job: %s", job)
    transport.send_message(workers.peers[0], master_identity, job)


def _run(transport, master_identity, workers, targets):
    for tgt in targets:
        _start_job(transport, master_identity, workers, tgt.job)


def _compile(transport, master_identity, workers, workspace_path):
    log.info("Loading workspace: %s", workspace_path)
    workspace = Workspace.from_yaml_file(workspace_path)
    project_to_tree = workspace.load_file_tree()
    manual_modules, compiled_modules = _collect_modules(project_to_tree)
    log.info("%d compiled modules", len(compiled_modules))
    resources, sources = load_resources(workspace.projects, project_to_tree)
    log.info("loaded %d resources, %d sources", len(resources), len(sources))
    targets = _create_targets(compiled_modules, project_to_tree)
    log.info("%d targets", len(targets))
    _run(transport, master_identity, workers, targets)
