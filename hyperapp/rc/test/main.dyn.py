import logging

from .code.source_path import pick_source_path_assoc

log = logging.getLogger(__name__)


def main(
        assoc_pickers,
        assoc_implanter,
        identity_creg,
        compile_resources,
        workspace_path,
        ):
    assoc_pickers.append(pick_source_path_assoc)
    assoc_implanter.init()
    compile_resources(workspace_path)
