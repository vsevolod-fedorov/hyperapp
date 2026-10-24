import argparse
import logging
from pathlib import Path

from hyperapp.boot.resource.workspace import Workspace

from .code.source_path import pick_source_path_assoc

log = logging.getLogger(__name__)

DEFAULT_WORKER_COUNT = 2


def _parse_args(sys_argv):
    parser = argparse.ArgumentParser(description='Compile resources')
    parser.add_argument('workspace', type=Path, help="Path to workspace file")
    parser.add_argument(
        '--workers', type=int, default=DEFAULT_WORKER_COUNT,
        help=f"Subprocess worker count, default is {DEFAULT_WORKER_COUNT}")
    args = parser.parse_args(sys_argv)
    return args


def _write_tree(projects, project_to_tree):
    for project_name, tree in project_to_tree.items():
        for file_path, data in sorted(tree.items()):
            path = projects[project_name].path.joinpath(*file_path)
            log.info("Write %s", path)
            path.write_bytes(data)


def main(
        assoc_pickers,
        assoc_implanter,
        compile_resources,
        sys_argv,
        ):
    assoc_pickers.append(pick_source_path_assoc)
    assoc_implanter.init()
    args = _parse_args(sys_argv)
    log.info("Loading workspace: %s", args.workspace)
    workspace = Workspace.from_yaml_file(args.workspace)
    result = compile_resources(workspace.projects, workspace.load_file_tree(), args.workers)
    _write_tree(workspace.projects, result.resource_tree)
