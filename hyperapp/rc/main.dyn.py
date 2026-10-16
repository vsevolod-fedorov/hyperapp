import argparse
import logging
from pathlib import Path

from hyperapp.boot.resource.workspace import Workspace

from .code.source_path import pick_source_path_assoc

log = logging.getLogger(__name__)


def _parse_args(sys_argv):
    parser = argparse.ArgumentParser(description='Compile resources')
    parser.add_argument('workspace', type=Path, help="Path to workspace file")
    args = parser.parse_args(sys_argv)
    return args


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
    compile_resources(workspace.projects, workspace.load_file_tree())
