from pathlib import Path

from hyperapp.boot.boot import boot
from hyperapp.boot.resource.workspace import Workspace

TEST_DIR = Path(__file__).parent.resolve()
RESOURCES_ROOT = TEST_DIR / 'resources'
PROJECTS_PATH = TEST_DIR / 'projects.yaml'


def _compile(workspace_name):
    workspace = Workspace.from_yaml_file(RESOURCES_ROOT / workspace_name / 'workspace.yaml')
    compile_resources = boot(PROJECTS_PATH, 'rc_test:boot:boot.attr')
    compile_resources(workspace.projects, workspace.load_file_tree())


def test_empty_module():
    _compile('empty_module')


def test_code_import():
    _compile('code_import')
