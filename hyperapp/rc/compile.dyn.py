import logging

from hyperapp.boot.resource.workspace import Workspace, load_file_tree

from .services import (
    load_resources,
    )
from .code.module import Module
from .code.transport import LocalEndpoint

log = logging.getLogger(__name__)


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
            master_identity, 'sample', count=2, timeout_sec=5, start_timeout_sec=5) as workers:
        log.info("workers are running: %s", workers.peers)
        _compile(workers, workspace_path)
    log.info("workers are finished")


def _compile(workers, workspace_path):
    log.info("Loading workspace: %s", workspace_path)
    workspace = Workspace.from_yaml_file(workspace_path)
    project_to_tree = workspace.load_file_tree()
    resources, sources = load_resources(workspace.projects, project_to_tree)
