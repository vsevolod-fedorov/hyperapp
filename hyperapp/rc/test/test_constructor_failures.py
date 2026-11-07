import pytest

from constructor_job_support import config_for_tests, recorded_module, run_import, run_test
from test_probe_jobs import worker


def _import_provider(worker, at_send):
    return run_import(worker, 'subject', 'subject_call', at_send=at_send)


def _import_test_module(worker, at_send):
    cfg = config_for_tests(worker, {'subject': recorded_module(worker, 'subject')})
    return run_import(worker, 'checks', 'checks_retry', cfg_items=cfg, at_send=at_send)


def _test_function(worker, at_send):
    cfg = config_for_tests(worker, {'subject': recorded_module(worker, 'subject')})
    return run_test(worker, cfg_items=cfg, at_send=at_send)


# Each failure boundary has the same contract for all three job entry paths.
@pytest.fixture(params=[_import_provider, _import_test_module, _test_function])
def run_job(request, worker, monkeypatch):
    contexts = []
    original = worker.probe.ProbeContext.__enter__

    def enter(context):
        contexts.append(context)
        return original(context)

    monkeypatch.setattr(worker.probe.ProbeContext, '__enter__', enter)

    def check_cleanup():
        assert contexts
        for context in contexts:
            assert context.discoveries.entries == ()
            assert context._states == {}
            assert context._resolve_service is None

    return lambda: request.param(worker, check_cleanup)


def _fail(*args, **kw):
    raise RuntimeError('injected failure')


def _assert_internal_error(worker, result):
    assert isinstance(result, (
        worker.imports.htypes.import_job.internal_error_result,
        worker.tests.htypes.test_job.internal_error_result,
        ))
    assert 'injected failure' in result.error
    assert not hasattr(result, 'constructors')


def test_snapshot_failure_discards_constructors(worker, monkeypatch, run_job):
    monkeypatch.setattr(worker.imports.code.ctr_collector.CtrCollector, 'snapshot', _fail)
    _assert_internal_error(worker, run_job())


def test_discovery_sink_failure_discards_constructors(worker, monkeypatch, run_job):
    collector = worker.imports.code.ctr_collector
    original = worker.probe.DiscoverySink.add

    def add(sink, entry):
        if isinstance(entry, collector.ConstructorDiscovery):
            _fail()
        original(sink, entry)

    monkeypatch.setattr(worker.probe.DiscoverySink, 'add', add)
    _assert_internal_error(worker, run_job())


def test_observation_serialization_failure_discards_constructors(worker, monkeypatch, run_job):
    collector = worker.imports.code.ctr_collector
    original = collector.constructor_ref

    def serialize(ctr):
        # Declarations succeed first, so a late error must discard the entire snapshot.
        if ctr.key.startswith('call:'):
            _fail()
        return original(ctr)

    monkeypatch.setattr(collector, 'constructor_ref', serialize)
    _assert_internal_error(worker, run_job())


def test_requirement_failure_discards_constructors(worker, monkeypatch, run_job):
    monkeypatch.setattr(worker.imports, 'enum_import_requirements', _fail)
    monkeypatch.setattr(worker.tests, 'enum_import_requirements', _fail)
    _assert_internal_error(worker, run_job())


def test_cleanup_failure_discards_constructors(worker, monkeypatch, run_job):
    original = worker.probe.ProbeContext.__exit__

    def exit(context, *args):
        original(context, *args)
        _fail()

    monkeypatch.setattr(worker.probe.ProbeContext, '__exit__', exit)
    _assert_internal_error(worker, run_job())


@pytest.mark.parametrize('program,outcome', [
    ('subject_failed', 'failed_result'),
    ('subject_incomplete', 'incomplete_result'),
    ])
def test_aborted_provider_import_publishes_nothing(worker, program, outcome):
    result = run_import(worker, 'subject', program)
    assert isinstance(result, worker.animate(f'rc:job/import.t:{outcome}'))
    assert not hasattr(result, 'constructors')


@pytest.mark.parametrize('program,outcome', [
    ('checks_failed', 'failed_result'),
    ('checks_incomplete', 'incomplete_result'),
    ])
def test_aborted_test_module_import_publishes_nothing(worker, program, outcome):
    cfg = config_for_tests(worker, {'subject': recorded_module(worker, 'subject')})
    result = run_import(worker, 'checks', program, cfg_items=cfg)
    assert isinstance(result, worker.animate(f'rc:job/import.t:{outcome}'))
    assert not hasattr(result, 'constructors')


@pytest.mark.parametrize('program,function,outcome', [
    ('checks', 'test_fail', 'failed_result'),
    ('checks_test_incomplete', 'test_incomplete', 'incomplete_result'),
    ])
def test_aborted_test_function_publishes_nothing(worker, program, function, outcome):
    cfg = config_for_tests(worker, {'subject': recorded_module(worker, 'subject')})
    result = run_test(worker, function, source_name=program, cfg_items=cfg)
    assert isinstance(result, worker.animate(f'rc:job/test.t:{outcome}'))
    assert not hasattr(result, 'constructors')


def test_declaration_serialization_failure_is_internal(worker, monkeypatch):
    monkeypatch.setattr(worker.imports.code.ctr_collector, 'constructor_ref', _fail)
    _assert_internal_error(worker, run_import(worker, 'subject'))


@pytest.mark.parametrize('function,is_async,is_generator', [
    ('test_async_failure', True, False),
    ('test_generator_failure', False, True),
    ('test_async_generator_failure', True, True),
    ])
def test_late_execution_failure_discards_observations(worker, function, is_async, is_generator):
    cfg = config_for_tests(worker, {'subject': recorded_module(worker, 'subject')})
    result = run_test(worker, function, cfg_items=cfg, is_async=is_async, is_generator=is_generator)
    assert isinstance(result, worker.tests.htypes.test_job.failed_result)
    assert 'late failure' in result.error
    assert not hasattr(result, 'constructors')


def test_discovery_failure_discards_declarations(worker):
    result = run_import(worker, 'subject', 'subject_discovery_failure')
    assert isinstance(result, worker.imports.htypes.import_job.failed_result)
    assert 'Wrapper cycle' in result.error
    assert not hasattr(result, 'constructors')
