import argparse
import logging
from pathlib import Path

from hyperapp.boot.resource.workspace import Workspace, load_file_tree

from .services import (
    load_resources,
    )
from .code.source_path import pick_source_path_assoc
from .code.transport import LocalEndpoint

log = logging.getLogger(__name__)


def compile_resources(workspace_path):
    log.info("Loading workspace: %s", workspace_path)
    workspace = Workspace.from_yaml_file(workspace_path)
    project_to_tree = workspace.load_file_tree()
    resources, sources = load_resources(workspace.projects, project_to_tree)


def _parse_args(sys_argv):
    parser = argparse.ArgumentParser(description='Compile resources')
    parser.add_argument('workspace', type=Path, help="Path to workspace file")
    args = parser.parse_args(sys_argv)
    return args


def main(
        assoc_pickers,
        assoc_implanter,
        identity_creg,
        generate_rsa_identity,
        subprocess_workers_running,
        selectors,
        transport,
        message_creg,
        compile_resources,
        sys_argv,
        ):
    assoc_pickers.append(pick_source_path_assoc)
    assoc_implanter.init()
    args = _parse_args(sys_argv)
    compile_resources(args.workspace)
    master_identity = generate_rsa_identity(fast=True)
    transport.add_endpoint(master_identity.peer, LocalEndpoint(message_creg, master_identity))
    log.info("master identity: %s", master_identity)
    with subprocess_workers_running(
            master_identity, 'sample', count=2, timeout_sec=5, start_timeout_sec=5) as workers:
        log.info("workers are running: %s", workers.peers)
        selectors.run(1)
    log.info("workers are finished")
