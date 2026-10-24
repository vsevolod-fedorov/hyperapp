import logging
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
# Logged by compile for each target; test results are not in the result tree, so they are got from these.
TARGET_STATE_MSG = "Target %s: %s"


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


def _target_states(caplog):
    return {
        record.args[0]: record.args[1]
        for record in caplog.records
        if record.msg == TARGET_STATE_MSG
        }


# Test targets must be just expected ones; other targets are checked only when expected.
# Without expected errors, no errors must be logged at all.
def _check_log(caplog, expected_states, expected_errors):
    states = _target_states(caplog)
    assert {name: states.get(name) for name in expected_states} == expected_states
    test_names = {name for name in states if name.startswith('test/')}
    assert test_names == {name for name in expected_states if name.startswith('test/')}
    errors = [record.getMessage() for record in caplog.records if record.levelno >= logging.ERROR]
    if not expected_errors:
        assert not errors
    for expected in expected_errors:
        assert any(expected in error for error in errors), expected
    caplog.clear()


def _compile_and_check(caplog, workspace_name, expected_states=None, expected_errors=()):
    expected_states = expected_states or {}
    workspace = Workspace.from_yaml_file(RESOURCES_ROOT / workspace_name / 'workspace.yaml')
    project_to_tree = workspace.load_file_tree()
    expected_tree = _expected_tree(project_to_tree)
    # Single boot: dyn modules from one boot can not be imported again by another in the same process.
    compile_resources = boot(PROJECTS_PATH, 'rc_test:boot:boot.attr')
    result_tree = compile_resources(workspace.projects, project_to_tree)
    assert result_tree == expected_tree
    _check_log(caplog, expected_states, expected_errors)
    # Second run gets resources made by the first one; they must load and stay the same.
    updated_tree = {
        project_name: {**tree, **result_tree.get(project_name, {})}
        for project_name, tree in project_to_tree.items()
        }
    result_tree = compile_resources(workspace.projects, updated_tree)
    assert result_tree == expected_tree
    _check_log(caplog, expected_states, expected_errors)


def test_empty_module(caplog):
    _compile_and_check(caplog, 'empty_module')


def test_code_import(caplog):
    _compile_and_check(caplog, 'code_import')


def test_code_paths(caplog):
    _compile_and_check(caplog, 'code_paths')


# Modules 2 and 3 use imported objects at import time; they are imported again
# with those imports resolved to real modules.
def test_code_import_incomplete(caplog):
    _compile_and_check(caplog, 'code_import_incomplete')


# Test module imports tested modules with 'tested.code' prefix.
def test_test_collection(caplog):
    test_states = {
        f'test/sample/modules.tests/{name}': 'resolved'
        for name in [
            'test_fn_1',
            'test_fn_2',
            'test_both_fns',
            ]
        }
    _compile_and_check(caplog, 'test_collection', test_states)
