import logging

from hyperapp.boot.resource.workspace import Workspace, load_file_tree

from .services import (
    load_resources,
    )
from .code.module import Module

log = logging.getLogger(__name__)


def compile_resources(workspace_path):
    log.info("Loading workspace: %s", workspace_path)
    workspace = Workspace.from_yaml_file(workspace_path)
    project_to_tree = workspace.load_file_tree()
    resources, sources = load_resources(workspace.projects, project_to_tree)
