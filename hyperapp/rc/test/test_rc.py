from pathlib import Path

from hyperapp.boot.boot import boot
from hyperapp.boot.resource.workspace import Workspace

TEST_DIR = Path(__file__).parent.resolve()
RESOURCES_ROOT = TEST_DIR / 'resources'
# Expected resource files lie beside sources. Not named *.resources.yaml:
# rc_test project would load them as its own resources, and compiler would take them as manual.
EXPECTED_SUFFIX = '.resources.expected.yaml'
RESOURCES_SUFFIX = '.resources.yaml'
PROJECTS_PATH = TEST_DIR / 'projects.yaml'


def _expected_tree(project_to_tree):
    project_to_expected = {}
    for project_name, tree in project_to_tree.items():
        expected = {
            (*file_path[:-1], file_path[-1][:-len(EXPECTED_SUFFIX)] + RESOURCES_SUFFIX): data
            for file_path, data in tree.items()
            if file_path[-1].endswith(EXPECTED_SUFFIX)
            }
        if expected:
            project_to_expected[project_name] = expected
    return project_to_expected


def _compile_and_check(workspace_name):
    workspace = Workspace.from_yaml_file(RESOURCES_ROOT / workspace_name / 'workspace.yaml')
    project_to_tree = workspace.load_file_tree()
    expected_tree = _expected_tree(project_to_tree)
    # Single boot: dyn modules from one boot can not be imported again by another in the same process.
    compile_resources = boot(PROJECTS_PATH, 'rc_test:boot:boot.attr')
    result_tree = compile_resources(workspace.projects, project_to_tree)
    assert result_tree == expected_tree
    # Second run gets resources made by the first one; they must load and stay the same.
    updated_tree = {
        project_name: {**tree, **result_tree.get(project_name, {})}
        for project_name, tree in project_to_tree.items()
        }
    result_tree = compile_resources(workspace.projects, updated_tree)
    assert result_tree == expected_tree


def test_empty_module():
    _compile_and_check('empty_module')


def test_code_import():
    _compile_and_check('code_import')


def test_code_paths():
    _compile_and_check('code_paths')
