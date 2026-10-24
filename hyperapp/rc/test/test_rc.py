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


# Test alias target names have no run index suffix, unlike test run ones.
def _is_test_alias(name):
    return name.startswith('test/') and not name.rsplit('/', 1)[-1].isdigit()


# Test aliases must be just expected ones; other targets are checked only when expected.
# Without expected errors, no errors must be logged at all.
def _check_log(caplog, expected_states, expected_errors):
    states = _target_states(caplog)
    assert {name: states.get(name) for name in expected_states} == expected_states
    test_names = {name for name in states if _is_test_alias(name)}
    assert test_names == {name for name in expected_states if _is_test_alias(name)}
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


# Test module imports tested modules with 'tested.code' prefix, so it is a test one, giving no resources.
# Tested module_3 imports tested module_1, and untested module_4.
def test_test_collection(caplog):
    test_states = {
        f'test/sample/modules.tests/{name}': 'resolved'
        for name in [
            'test_fn_1',
            'test_fn_2',
            'test_both_fns',
            'test_fn_3',
            'test_async',
            'test_generator',
            'test_async_generator',
            'test_code_used_by_run',
            ]
        }
    # Alias follows the last run.
    test_states['test/sample/modules.tests/test_code_used_by_run/0'] = 'resolved'
    test_states['test/sample/modules.tests/test_code_used_by_run/1'] = 'resolved'
    _compile_and_check(caplog, 'test_collection', test_states)


# Tests use a module not tested by their test module import, so fail.
# Failed tests fail module_1 they test, and so its project: no resources are produced.
def test_tested_used_by_test_run(caplog):
    test_states = {
        f'test/sample/late.tests/{name}': 'failed'
        for name in [
            'test_async',
            'test_generator',
            'test_async_generator',
            ]
        }
    _compile_and_check(caplog, 'tested_used_by_test_run', test_states, [
        "Tested module tested.code.module_2.fn_2 is first used when the test runs",
        ])


# First import attempts are incomplete before tested imports, which later attempts find, so they fail.
def test_tested_imported_late(caplog):
    states = {
        'import/sample/late_compiled/1': 'failed',
        'import/sample/late_import.tests/1': 'failed',
        }
    _compile_and_check(caplog, 'tested_imported_late', states, [
        "late_compiled/1>: Tested modules are imported by import attempt #1 only: tested.code.module_1.",
        "late_import.tests/1>: Tested modules are imported by import attempt #1 only: tested.code.module_2.",
        ])


# Tested module uses an import only when the test runs, so it is not resolved for it, and the test fails.
def test_tested_import_used_by_test_run(caplog):
    states = {
        'test/sample/lazy.tests/test_fn': 'failed',
        }
    _compile_and_check(caplog, 'tested_import_used_by_test_run', states, [
        "Tested module sample:lazy uses code.module_1.fn_1 when the test runs, but not when it is imported",
        ])


# Tested module imports another tested one through an untested one: a dependency cycle, failing them all.
def test_tested_imported_indirectly(caplog):
    states = {
        'test/sample/indirect.tests/test_fn': 'failed',
        'module/compiled/sample/module_a': 'failed',
        'module/compiled/sample/module_b': 'failed',
        }
    _compile_and_check(caplog, 'tested_imported_indirectly', states, [
        "Dependency cycle: module/compiled/sample/module_b -> module/test/sample/indirect.tests"
        " -> module/compiled/sample/module_c -> module/compiled/sample/module_b",
        ])


# Whether a module is a test one is decided by its tested code imports, not by its name.
def test_test_module_by_imports(caplog):
    states = {
        'module/compiled/sample/plain.tests': 'resolved',
        'test/sample/checks/test_fn_1': 'resolved',
        }
    _compile_and_check(caplog, 'test_module_by_imports', states)
