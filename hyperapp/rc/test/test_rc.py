import logging
from pathlib import Path

import pytest

from hyperapp.boot.boot import boot
from hyperapp.boot.resource.workspace import Workspace

TEST_DIR = Path(__file__).parent.resolve()
RESOURCES_ROOT = TEST_DIR / 'resources'
# Expected resource files lie beside sources. Not named *.resources.yaml:
# rc_test project would load them as its own resources, and compiler would take them as manual.
EXPECTED_SUFFIX = '.resources.expected.yaml'
RESOURCES_SUFFIX = '.resources.yaml'
PROJECTS_PATH = TEST_DIR / 'projects.yaml'
# Faster for these small workspaces: starting workers takes longer than their jobs.
DEFAULT_WORKER_COUNT = 1
BASE_SUPPORT_PATHS = {
    ('mark.dyn.py',),
    ('mark.resources.yaml',),
    }


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


# Test alias target names have no run index suffix, unlike test run ones.
def _is_test_alias(name):
    return name.startswith('test/') and not name.rsplit('/', 1)[-1].isdigit()


# Test aliases must be just expected ones; other targets are checked only when expected.
# Errors and cycles must be just the expected ones. An error string matches a substring;
# a list checks all diagnostic lines for that target, in order.
def _check_result(result, expected_states, expected_errors, expected_cycles):
    states = {name: state.name.lower() for name, state in result.target_states.items()}
    assert states['all'] == ('failed' if expected_errors or expected_cycles else 'resolved')
    assert result.succeeded == (states['all'] == 'resolved')
    assert {name: states.get(name) for name in expected_states} == expected_states
    test_names = {name for name in states if _is_test_alias(name)}
    assert test_names == {name for name in expected_states if _is_test_alias(name)}
    assert result.errors.keys() == expected_errors.keys(), result.errors
    for name, expected in expected_errors.items():
        if isinstance(expected, str):
            assert expected in result.errors[name], (name, result.errors[name])
        else:
            assert result.errors[name].splitlines() == expected, name
    assert result.cycles == expected_cycles


def _compile_and_check(
        workspace_name, expected_states=None, expected_errors=None, expected_cycles=None,
        worker_count=DEFAULT_WORKER_COUNT, expected_constructors=None):
    expected_states = expected_states or {}
    expected_errors = expected_errors or {}
    expected_cycles = expected_cycles or []
    workspace = Workspace.from_yaml_file(RESOURCES_ROOT / workspace_name / 'workspace.yaml')
    project_to_tree = workspace.load_file_tree()
    if 'base' in project_to_tree:
        # Marker workspaces need only code.mark from the host base project; compiling the whole
        # project would pull in features unrelated to these focused workspaces.
        project_to_tree['base'] = {
            path: data
            for path, data in project_to_tree['base'].items()
            if path in BASE_SUPPORT_PATHS
            }
    expected_tree = _expected_tree(project_to_tree)
    # Single boot: dyn modules from one boot can not be imported again by another in the same process.
    compile_resources = boot(PROJECTS_PATH, 'rc_test:boot:boot.attr')
    result = compile_resources(workspace.projects, project_to_tree, worker_count)
    assert result.resource_tree == expected_tree, result.errors
    _check_result(result, expected_states, expected_errors, expected_cycles)
    _check_constructors(result, expected_constructors)
    # Second run gets resources made by the first one; they must load and stay the same.
    updated_tree = {
        project_name: {**tree, **result.resource_tree.get(project_name, {})}
        for project_name, tree in project_to_tree.items()
        }
    result = compile_resources(workspace.projects, updated_tree, worker_count)
    assert result.resource_tree == expected_tree, result.errors
    _check_result(result, expected_states, expected_errors, expected_cycles)
    _check_constructors(result, expected_constructors)


def _check_constructors(result, expected):
    if expected is None:
        return
    assert {
        str(path): {piece.key: piece.value for piece in pieces}
        for path, pieces in result.constructors.items()
        } == expected


@pytest.mark.parametrize('worker_count', [1, 4])
def test_constructors(worker_count):
    states = {
        'test/sample/constructors.tests/test_first': 'resolved',
        'test/sample/constructors.tests/test_repeat': 'resolved',
        'test/sample/constructors.tests/test_async': 'resolved',
        'test/sample/constructors.tests/test_generator': 'resolved',
        'test/sample/constructors.tests/test_async_generator': 'resolved',
        }
    expected = {
        'sample:first': {'declare:value': 'declared', 'call:value': 'first'},
        'sample:second': {'declare:value': 'declared', 'call:value': 'second'},
        }
    _compile_and_check('constructors', states, worker_count=worker_count, expected_constructors=expected)


@pytest.mark.parametrize('worker_count', [1, 4])
def test_constructors_only_from_own_project(worker_count):
    states = {
        'import/sample/subjects.tests/1': 'resolved',
        'test/sample/subjects.tests/test_both': 'resolved',
        }
    expected = {
        'library:subject': {'declare:value': 'declared'},
        'sample:subject': {'declare:value': 'declared', 'call:value': 'local'},
        }
    _compile_and_check('constructor_projects', states, worker_count=worker_count, expected_constructors=expected)


@pytest.mark.parametrize('worker_count', [1, 4])
def test_constructor_conflict(worker_count):
    states = {
        'import/sample/subject/1': 'failed',
        'module/compiled/sample/subject': 'failed',
        }
    errors = {'import/sample/subject/1': "Conflicting constructor sample:subject: 'call:value'"}
    _compile_and_check('constructor_conflict', states, errors, worker_count=worker_count, expected_constructors={})


@pytest.mark.parametrize('worker_count', [1, 4])
def test_constructor_import_cache(worker_count):
    states = {
        'test/sample/import_cache.tests/test_0': 'resolved',
        'test/sample/import_cache.tests/test_1': 'resolved',
        'test/sample/import_cache.tests/test_2': 'resolved',
        'test/sample/import_cache.tests/test_3': 'resolved',
        }
    expected = {
        'sample:subject': {
            'declare:import_only': 'declared',
            'call:import_only': 'ok',
            'declare:f0': 'declared',
            'declare:f1': 'declared',
            'declare:f2': 'declared',
            'declare:f3': 'declared',
            'call:f0': 'ok',
            'call:f1': 'ok',
            'call:f2': 'ok',
            'call:f3': 'ok',
            },
        'sample:other': {'declare:value': 'declared', 'call:value': 'ok'},
        }
    _compile_and_check('constructor_import_cache', states, worker_count=worker_count, expected_constructors=expected)


@pytest.mark.parametrize('worker_count', [1, 4])
def test_markers(worker_count):
    states = {
        'test/sample/marked.tests/test_tested_module_markers': 'resolved',
        }
    _compile_and_check('markers', states, worker_count=worker_count)


def test_unknown_marker_fails_only_active_module():
    states = {
        'import/sample/unknown/0': 'resolved',
        'import/sample/unknown/1': 'failed',
        'import/sample/valid/0': 'resolved',
        }
    errors = {
        'import/sample/unknown/1': "Unknown marker 'test.missing' for module sample:unknown",
        }
    _compile_and_check('marker_unknown', states, errors)


def test_marker_state_is_cleaned_after_incomplete_import():
    states = {
        'import/sample/a_incomplete/0': 'resolved',
        'import/sample/a_incomplete/1': 'resolved',
        'import/sample/z_valid/0': 'resolved',
        'module/compiled/sample/a_incomplete': 'resolved',
        'module/compiled/sample/z_valid': 'resolved',
        }
    _compile_and_check('marker_incomplete', states)


def test_marker_state_is_cleaned_between_test_jobs():
    states = {
        'test/sample/subject.tests/test_a_incomplete': 'resolved',
        'test/sample/subject.tests/test_a_incomplete/0': 'resolved',
        'test/sample/subject.tests/test_a_incomplete/1': 'resolved',
        'test/sample/subject.tests/test_b_failure': 'failed',
        'test/sample/subject.tests/test_c_success': 'resolved',
        }
    errors = {
        'test/sample/subject.tests/test_b_failure/0': 'Test failed: RuntimeError: expected test failure',
        }
    _compile_and_check('marker_test_isolation', states, errors)


@pytest.mark.parametrize('worker_count', [1, 4])
def test_probes(worker_count):
    states = {
        'import/sample/subject/0': 'resolved',
        'import/sample/subject/1': 'resolved',
        'module/compiled/sample/subject': 'resolved',
        'test/sample/subject.tests/test_cached_probe': 'resolved',
        'test/sample/subject.tests/test_bound_probes': 'resolved',
        'test/sample/subject.tests/test_sync_wrapped': 'resolved',
        'test/sample/subject.tests/test_async_wrapped': 'resolved',
        'test/sample/subject.tests/test_generator_wrapped': 'resolved',
        'test/sample/subject.tests/test_async_generator_wrapped': 'resolved',
        }
    _compile_and_check('probes', states, worker_count=worker_count)


@pytest.mark.parametrize('worker_count', [1, 4])
def test_probe_import_retries(worker_count):
    states = {
        'import/sample/provider/1': 'resolved',
        'import/sample/provider.tests/0': 'resolved',
        'import/sample/provider.tests/1': 'resolved',
        'import/sample/provider.tests/2': 'resolved',
        'test/sample/provider.tests/test_ok': 'resolved',
        }
    _compile_and_check('probe_import_retries', states, worker_count=worker_count)


@pytest.mark.parametrize('worker_count', [1, 4])
def test_probe_job_isolation(worker_count):
    states = {
        'import/sample/a_incomplete/1': 'resolved',
        'import/sample/a_incomplete/2': 'resolved',
        'import/sample/b_failure/1': 'failed',
        'test/sample/subject.tests/test_a_incomplete': 'resolved',
        'test/sample/subject.tests/test_a_incomplete/0': 'resolved',
        'test/sample/subject.tests/test_a_incomplete/1': 'resolved',
        'test/sample/subject.tests/test_b_failure': 'failed',
        'test/sample/subject.tests/test_c_success': 'resolved',
        'test/sample/subject.tests/test_generator': 'failed',
        'test/sample/subject.tests/test_async_generator': 'failed',
        'test/sample/subject.tests/test_params': 'failed',
        }
    errors = {
        'import/sample/b_failure/1': 'expected import failure',
        'test/sample/subject.tests/test_b_failure/0': 'RuntimeError: expected test failure',
        'test/sample/subject.tests/test_generator/0': 'RuntimeError: generator exhausted',
        'test/sample/subject.tests/test_async_generator/0': 'RuntimeError: async generator exhausted',
        'test/sample/subject.tests/test_params/0':
            'Fixtures are not supported yet; test has params: first, second, third',
        }
    _compile_and_check('probe_isolation', states, errors, worker_count=worker_count)


def test_empty_module():
    _compile_and_check('empty_module')


def test_generated_resources_without_source():
    workspace = Workspace.from_yaml_file(RESOURCES_ROOT / 'empty_module' / 'workspace.yaml')
    tree = workspace.load_file_tree()
    tree['sample']['old', 'a_module.resources.yaml'] = tree['sample']['a_module.resources.expected.yaml',]
    compile_resources = boot(PROJECTS_PATH, 'rc_test:boot:boot.attr')
    with pytest.raises(ValueError) as error:
        compile_resources(workspace.projects, tree, DEFAULT_WORKER_COUNT)
    assert str(error.value) == 'Generated file sample:old/a_module.resources.yaml has no source old/a_module.dyn.py'


@pytest.mark.parametrize('worker_count', [1, 4])
def test_test_module_imports_are_rejected(worker_count):
    states = {
        'imports/sample': 'resolved',
        'module/compiled/sample/code_import': 'failed',
        'module/test/sample/code_import.tests': 'failed',
        'test/sample/code_import.tests/test_import': 'failed',
        'import/sample/code_import_retry.tests/0': 'resolved',
        'import/sample/code_import_retry.tests/1': 'failed',
        'module/test/sample/code_import_retry.tests': 'failed',
        'import/sample/retry_import/1': 'failed',
        'module/test/sample/test_as_subject.tests': 'failed',
        'test/sample/test_as_subject.tests/test_checks': 'failed',
        'test/sample/checks/test_ok': 'resolved',
        }
    errors = {
        'module/compiled/sample/code_import': 'Test module sample:checks cannot be imported as code',
        'import/sample/retry_import/1': 'Test module sample:checks cannot be imported as code',
        'module/test/sample/test_as_subject.tests': 'Test module sample:checks cannot be imported as tested code',
        }
    _compile_and_check('test_module_imports', states, errors, worker_count=worker_count)


@pytest.mark.parametrize('worker_count', [1, 4])
def test_module_classification_across_projects(worker_count):
    states = {
        'module/compiled/library/subject': 'resolved',
        'project/library': 'resolved',
        'project/sample': 'failed',
        'test/library/subject.tests/test_value': 'resolved',
        'import/sample/consumer.tests/1': 'resolved',
        'module/test/sample/consumer.tests': 'resolved',
        'test/sample/consumer.tests/test_ok': 'resolved',
        'test/sample/consumer.tests/test_consumer_needs_web': 'failed',
        }
    errors = {'test/sample/consumer.tests/test_consumer_needs_web/0': 'consumer expected web'}
    _compile_and_check('classification_projects', states, errors, worker_count=worker_count)


@pytest.mark.parametrize('worker_count', [1, 4])
def test_failed_importing_project_preserves_provider_resources(worker_count):
    states = {
        'import/sample/broken/0': 'failed',
        'imports/sample': 'failed',
        'module/test/sample/consumer.tests': None,
        'module/compiled/library/subject': 'resolved',
        'project/library': 'resolved',
        'project/sample': 'failed',
        'module/compiled/independent/other': 'resolved',
        }
    errors = {'import/sample/broken/0': 'broken first import'}
    _compile_and_check('classification_failed_importer', states, errors, worker_count=worker_count)


def test_code_import():
    _compile_and_check('code_import')


def test_code_paths():
    _compile_and_check('code_paths')


# Modules 2 and 3 use imported objects at import time; they are imported again
# with those imports resolved to real modules.
def test_code_import_incomplete():
    _compile_and_check('code_import_incomplete')


# Test module imports tested modules with 'tested.code' prefix, so it is a test one, giving no resources.
# Tested module_3 imports tested module_1, and untested module_4.
def test_test_collection():
    test_states = {
        'test/sample/modules.tests/test_fn_1': 'resolved',
        'test/sample/modules.tests/test_fn_2': 'resolved',
        'test/sample/modules.tests/test_both_fns': 'resolved',
        'test/sample/modules.tests/test_fn_3': 'resolved',
        'test/sample/modules.tests/test_async': 'resolved',
        'test/sample/modules.tests/test_generator': 'resolved',
        'test/sample/modules.tests/test_async_generator': 'resolved',
        # Alias follows the last run.
        'test/sample/modules.tests/test_code_used_by_run': 'resolved',
        'test/sample/modules.tests/test_code_used_by_run/0': 'resolved',
        'test/sample/modules.tests/test_code_used_by_run/1': 'resolved',
        }
    _compile_and_check('test_collection', test_states)


@pytest.mark.parametrize('worker_count', [1, 4])
def test_mixed_code_imports_fail_on_the_observing_attempt(worker_count):
    states = {
        'import/sample/manual.tests/0': 'failed',
        'import/library/mixed_retry.tests/0': 'resolved',
        'import/library/mixed_retry.tests/1': 'failed',
        'test/library/mixed_imports.tests/test_mixed_import_in_subject': 'failed',
        'test/library/mixed_imports.tests/test_code_alias_of_tested_module': 'failed',
        'test/library/mixed_imports.tests/test_code_alias_of_tested_module/1': None,
        'test/library/mixed_imports.tests/test_unforced_code_alias': 'failed',
        'test/library/mixed_imports.tests/test_unforced_code_alias/1': None,
        'test/library/mixed_imports.tests/test_tested_alias_of_plain_module': 'failed',
        'test/library/mixed_imports.tests/test_tested_alias_of_plain_module/1': None,
        }
    mixed_module_1 = 'library:mixed_imports.tests imports library:module_1 through both code and tested.code'
    errors = {
        'import/sample/manual.tests/0':
            'sample:manual.tests imports library:manual through both code and tested.code',
        'import/library/mixed_retry.tests/1':
            'library:mixed_retry.tests imports library:module_1 through both code and tested.code',
        'test/library/mixed_imports.tests/test_mixed_import_in_subject/0':
            'library:module_1 imports library:manual through both code and tested.code',
        'test/library/mixed_imports.tests/test_code_alias_of_tested_module/0': mixed_module_1,
        'test/library/mixed_imports.tests/test_unforced_code_alias/0': mixed_module_1,
        'test/library/mixed_imports.tests/test_tested_alias_of_plain_module/0':
            'library:mixed_imports.tests imports library:manual through both code and tested.code',
        }
    _compile_and_check('mixed_module_imports', states, errors, worker_count=worker_count)


# Tests use a module not tested by their test module import, so fail.
# Failed tests fail module_1 they test, and so its project: no resources are produced.
def test_tested_used_by_test_run():
    test_states = {
        'test/sample/late.tests/test_async': 'failed',
        'test/sample/late.tests/test_generator': 'failed',
        'test/sample/late.tests/test_async_generator': 'failed',
        'test/sample/late.tests/test_unforced_subject': 'failed',
        'test/sample/late.tests/test_late_manual': 'failed',
        }
    undeclared_module_2 = (
        'This test uses sample:module_2, but sample:late.tests did not declare it as a test subject.'
        ' Add `from .tested.code import module_2` at module level.')
    errors = {
        'test/sample/late.tests/test_async/0': undeclared_module_2,
        'test/sample/late.tests/test_generator/0': undeclared_module_2,
        'test/sample/late.tests/test_async_generator/0': undeclared_module_2,
        'test/sample/late.tests/test_unforced_subject/0': undeclared_module_2,
        'test/sample/late.tests/test_late_manual/0':
            'This test uses sample:manual, but sample:late.tests did not declare it as a test subject.'
            ' Add `from .tested.code import manual` at module level.',
        }
    _compile_and_check('tested_used_by_test_run', test_states, errors)


# First import attempts are incomplete before tested imports, which later attempts find, so they fail.
def test_tested_imported_late():
    states = {
        'import/sample/late_compiled/1': 'failed',
        'import/sample/late_import.tests/1': 'failed',
        }
    _compile_and_check('tested_imported_late', states, {
        'import/sample/late_compiled/1': "Tested modules are imported by import attempt #1 only: tested.code.module_1.",
        'import/sample/late_import.tests/1':
            "Tested modules are imported by import attempt #1 only: tested.code.module_2.",
        })


# Tested module uses an import only when the test runs, so it is not resolved for it, and the test fails.
# Other tests of its test module are not failed by that, whether they are run by the same worker or not:
# by one worker, all tests are; by 4, first runs of the 4 tests are run by a worker each.
@pytest.mark.parametrize('worker_count', [1, 4])
def test_tested_import_used_by_test_run(worker_count):
    states = {
        'test/sample/lazy.tests/test_fn': 'failed',
        'test/sample/lazy.tests/test_unforced_dependency': 'failed',
        'test/sample/lazy.tests/test_code_1': 'resolved',
        'test/sample/lazy.tests/test_code_2': 'resolved',
        'test/sample/lazy.tests/test_code_3': 'resolved',
        }
    _compile_and_check('tested_import_used_by_test_run', states, {
        'test/sample/lazy.tests/test_fn/0':
            "Tested module sample:lazy uses code.module_1.fn_1 when the test runs, but not when it is imported",
        'test/sample/lazy.tests/test_unforced_dependency/0':
            "Tested module sample:lazy uses code.module_1 when the test runs, but not when it is imported",
        }, worker_count=worker_count)


def test_cycle_between_recorded_subjects(caplog):
    left = 'module/compiled/sample/left'
    right = 'module/compiled/sample/right'
    states = {
        'import/sample/cycle.tests/0': 'resolved',
        'import/sample/cycle_retry.tests/0': 'resolved',
        'import/sample/cycle_retry.tests/1': 'failed',
        'module/test/sample/cycle.tests': 'failed',
        'test/sample/cycle.tests/test_pair': 'failed',
        left: 'failed',
        right: 'failed',
        }
    message = f"Dependency cycle: {left} -> {right} -> {left}"
    errors = {left: [message], right: [message]}
    _compile_and_check('tested_import_cycle', states, errors, [([left, right, left], None)])
    # One log per compile, even though both members carry the message.
    assert [r.getMessage() for r in caplog.records if r.levelno == logging.ERROR] == [message, message]


# Tested module imports another tested one through an untested one: a dependency cycle, failing them all.
def test_tested_imported_indirectly():
    subject = 'module/compiled/sample/module_b'
    untested = 'module/compiled/sample/module_c'
    checks = 'module/test/sample/indirect.tests'
    test = 'test/sample/indirect.tests/test_fn'
    run = f'{test}/0'
    states = {
        test: 'failed',
        'module/compiled/sample/module_a': 'failed',
        subject: 'failed',
        }
    hint = (
        "Tested module sample:module_b is imported by tested module sample:module_a"
        " through untested module sample:module_c. Being complete, sample:module_c requires complete"
        " sample:module_b, which waits for its tests. Tested modules may import each other only directly")
    module_cycle = [subject, checks, untested, subject]
    run_cycle = [subject, test, run, checks, untested, subject]
    module_error = f"Dependency cycle: {' -> '.join(module_cycle)}. {hint}"
    run_error = f"Dependency cycle: {' -> '.join(run_cycle)}. {hint}"
    errors = {
        subject: [module_error, run_error],
        checks: [module_error, run_error],
        untested: [module_error, run_error],
        test: [run_error],
        run: [run_error],
        }
    _compile_and_check('tested_imported_indirectly', states, errors, [(module_cycle, hint), (run_cycle, hint)])


# Whether a module is a test one is decided by its tested code imports, not by its name.
def test_test_module_by_imports():
    states = {
        'module/compiled/sample/plain.tests': 'resolved',
        'test/sample/checks/test_fn_1': 'resolved',
        }
    _compile_and_check('test_module_by_imports', states)


# Import of a module not found fails the importing module, not the whole compile.
def test_code_import_missing():
    states = {
        'import/sample/user/0': 'failed',
        }
    _compile_and_check('code_import_missing', states, {
        'import/sample/user/0': "sample:user: Module not found for import: code.missing",
        })


# Manual module is imported by its module resource, as written; tests of its importers get it too.
def test_manual_module_import():
    states = {
        'module/manual/sample/lib': 'resolved',
        'module/compiled/sample/user': 'resolved',
        'test/sample/user.tests/test_fn': 'resolved',
        }
    _compile_and_check('manual_module_import', states)


# Manual resources without a module resource can not be imported; their import fails the importing module.
def test_manual_module_no_resource():
    states = {
        'import/sample/user/0': 'failed',
        }
    _compile_and_check('manual_module_no_resource', states, {
        'import/sample/user/0': "sample:user: Manual module has no settings.module resource for import: code.settings",
        })


# Manual module is tested as it is: it is not compiled, so there is nothing to record its uses for.
def test_manual_module_tested():
    states = {
        'module/manual/sample/lib': 'resolved',
        'module/test/sample/lib.tests': 'resolved',
        'test/sample/lib.tests/test_fn': 'resolved',
        }
    _compile_and_check('manual_module_tested', states)


# Types are imported as htypes.<type module name>.<type name>, type module is found nearest to the importer.
# All types seen by a module are given to its imports and test runs, so using types never makes them incomplete:
# each is run once. Tested module shapes gets the line type only in a function, so only the test run finds it is used.
def test_type_import():
    states = {
        'import/sample/shapes/0': 'resolved',
        'import/sample/shapes/1': None,
        'module/compiled/sample/shapes': 'resolved',
        'module/compiled/sample/sub/nested': 'resolved',
        'test/sample/shapes.tests/test_line_to': 'resolved',
        'test/sample/shapes.tests/test_line_to/0': 'resolved',
        'test/sample/shapes.tests/test_line_to/1': None,
        }
    _compile_and_check('type_import', states)


# Types of an imported project are imported by its local name and type module path from its root, as code is;
# local type module named like the project shadows it.
def test_type_import_projects():
    states = {
        'module/compiled/sample/drawing': 'resolved',
        'module/compiled/sample/sub/shaded': 'resolved',
        }
    _compile_and_check('type_import_projects', states)


# Type import not resolved fails the importing module.
def test_type_import_missing():
    states = {
        'import/sample/no_module/0': 'failed',
        'import/sample/no_type/0': 'failed',
        'import/sample/no_type_name/0': 'failed',
        }
    _compile_and_check('type_import_missing', states, {
        'import/sample/no_module/0': "sample:no_module: Type module not found for import: htypes.missing.point",
        'import/sample/no_type/0':
            "sample:no_type: Type module sample:sample.t has no type missing for import: htypes.sample.missing",
        'import/sample/no_type_name/0': "sample:no_type_name: Type name is missing for import: htypes.sample",
        })


# Boot services are imported as services.<service name>, usually by from .services import (...).
# All are given to imports and test runs up front, like types, so using them never makes them incomplete:
# each is run once. Tested module codec uses web only in a function, so only the test run finds it is used.
def test_boot_service_import():
    states = {
        'import/sample/codec/0': 'resolved',
        'import/sample/codec/1': None,
        'module/compiled/sample/codec': 'resolved',
        'module/compiled/sample/sub/registry': 'resolved',
        'boot_service/mosaic': 'resolved',
        'boot_service/pyobj_creg': 'resolved',
        'boot_service/web': 'resolved',
        'test/sample/codec.tests/test_load': 'resolved',
        'test/sample/codec.tests/test_load/0': 'resolved',
        'test/sample/codec.tests/test_load/1': None,
        }
    _compile_and_check('boot_service_import', states)


# Boot service import not resolved fails the importing module.
def test_boot_service_import_missing():
    states = {
        'import/sample/user/0': 'failed',
        }
    _compile_and_check('boot_service_import_missing', states, {
        'import/sample/user/0': "sample:user: Boot service not found for import: services.missing",
        })
