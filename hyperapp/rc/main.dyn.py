import argparse
import logging
from pathlib import Path

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
    compile_resources(args.workspace)
