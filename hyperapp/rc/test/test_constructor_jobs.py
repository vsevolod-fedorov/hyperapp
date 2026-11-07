import gc
import logging
import weakref

import pytest

from constructor_job_support import (
    accepted, config_for_tests, handle, make_master, path, payloads, recorded_module,
    run_import, run_import_job, run_test, run_test_job, values,
    )
from test_probe_jobs import worker


@pytest.fixture
def declarations(worker, monkeypatch):
    support = worker.animate('rc_test:test_constructors:test_constructors.module')
    original = support.constructor_marker
    calls = []

    def marker(*args, **kw):
        calls.append(kw['path'])
        return original(*args, **kw)

    monkeypatch.setattr(support, 'constructor_marker', marker)
    return calls


def test_import_collects_constructors_and_ignores_opaque_discoveries(worker, monkeypatch):
    collector = worker.imports.code.ctr_collector
    original = collector.CtrCollector.snapshot

    class Opaque:
        @property
        def piece(self):
            raise AssertionError('Generic entries must stay opaque')

    def snapshot(self):
        self._context.discoveries.add(Opaque())
        return original(self)

    monkeypatch.setattr(collector.CtrCollector, 'snapshot', snapshot)
    result = run_import(worker, 'subject', 'subject_call')
    assert values(worker, result) == {
        ('sample:subject', 'declare:value'): 'declared',
        ('sample:subject', 'call:value'): 'ok',
        }


def test_repeated_import_result_preserves_constructor_instances(worker):
    master = make_master(worker, {'subject': 'subject_call'})
    result = run_import(worker, 'subject', 'subject_call')
    target = handle(master, result)
    assert target.state.name == 'RESOLVED'
    assert accepted(master) == {'sample:subject': {'declare:value': 'declared', 'call:value': 'ok'}}
    first = target.module_tgt.constructors
    handle(master, result)
    assert len(target.module_tgt.constructors) == 2
    assert all(a is b for a, b in zip(first, target.module_tgt.constructors))


def test_first_import_keeps_constructors_pending_until_classification(worker):
    master = make_master(worker, {'subject': 'subject_call', 'other': 'unused'})
    target = handle(master, run_import(worker, 'subject', 'subject_call'))
    assert target.state.name == 'RESOLVED'
    assert target.module_tgt is None
    assert accepted(master) == {}
    handle(master, run_import(worker, 'other', 'unused'))
    assert target.module_tgt.state.name == 'RESOLVED'
    assert accepted(master) == {'sample:subject': {'declare:value': 'declared', 'call:value': 'ok'}}


def test_deferred_import_failure_discards_its_constructors(worker):
    master = make_master(worker, {'subject': 'subject_missing_import', 'other': 'unused'})
    result = run_import(worker, 'subject', 'subject_missing_import')
    assert result.constructors
    target = handle(master, result)
    assert target.module_tgt is None
    assert accepted(master) == {}
    last = handle(master, run_import(worker, 'other', 'unused'))
    assert target.state.name == 'FAILED'
    assert 'Module not found for import: code.missing' in target.error
    assert last.state.name == 'RESOLVED'
    assert last.error is None
    assert accepted(master) == {}


def test_test_result_attributes_constructors_to_each_provider(worker):
    programs = {'subject': 'subject', 'other': 'other', 'checks': 'checks_both'}
    master = make_master(worker, programs)
    for name, program in programs.items():
        assert handle(master, run_import(worker, name, program)).state.name == 'RESOLVED'
    cfg = config_for_tests(worker, {
        'subject': recorded_module(worker, 'subject'),
        'other': recorded_module(worker, 'other'),
        })
    result = run_test(worker, 'test_both', source_name='checks_both', cfg_items=cfg)
    target = handle(master, result)
    assert target.state.name == 'RESOLVED', target.error
    assert accepted(master) == {
        'sample:subject': {'declare:value': 'declared', 'call:value': 'ok'},
        'sample:other': {'declare:second': 'declared', 'call:second': 'ok'},
        }


def test_failed_test_replays_declarations_but_not_observations(worker, declarations):
    cfg = config_for_tests(worker, {'subject': recorded_module(worker, 'subject')})
    failed = run_test(worker, 'test_fail', cfg_items=cfg)
    assert isinstance(failed, worker.tests.htypes.test_job.failed_result)
    assert not hasattr(failed, 'constructors')
    succeeded = run_test(worker, cfg_items=cfg)
    assert values(worker, succeeded) == {
        ('sample:subject', 'declare:value'): 'declared',
        ('sample:subject', 'call:value'): 'ok',
        }
    assert run_test(worker, cfg_items=cfg).constructors == succeeded.constructors
    assert declarations == [path(worker, 'subject')]


def test_import_retry_activates_tested_module_and_reuses_its_probe(worker, declarations):
    cfg = config_for_tests(worker, {'subject': recorded_module(worker, 'subject')})
    imported = run_import(worker, 'checks', 'checks_retry', cfg_items=cfg)
    expected = {
        ('sample:subject', 'declare:value'): 'declared',
        ('sample:subject', 'call:value'): 'ok',
        }
    assert values(worker, imported) == expected
    tested = run_test(worker, source_name='checks_retry', cfg_items=cfg)
    assert values(worker, tested) == expected
    assert run_test(worker, source_name='checks_retry', cfg_items=cfg).constructors == tested.constructors
    assert declarations == [path(worker, 'subject')]


def test_import_retry_activates_nested_tested_modules(worker, declarations):
    other = recorded_module(worker, 'other')
    subject = recorded_module(worker, 'subject', 'subject_nested', imports={'code.other': other})
    cfg = config_for_tests(worker, {'subject': subject, 'other': other})
    expected = {
        ('sample:subject', 'declare:value'): 'declared',
        ('sample:subject', 'call:value'): 'ok',
        ('sample:other', 'declare:second'): 'declared',
        ('sample:other', 'call:second'): 'ok',
        }
    imported = run_import(worker, 'checks', 'checks_nested', cfg_items=cfg)
    assert values(worker, imported) == expected
    tested = run_test(worker, source_name='checks_nested', cfg_items=cfg)
    assert values(worker, tested) == expected
    assert run_test(worker, source_name='checks_nested', cfg_items=cfg).constructors == tested.constructors
    assert declarations == [path(worker, 'other'), path(worker, 'subject')]


def test_import_retry_publishes_tested_constructors_but_not_test_module_ones(worker):
    master = make_master(worker, {'subject': 'subject', 'checks': 'checks_import_only'})
    handle(master, run_import(worker, 'subject'))
    handle(master, run_import(worker, 'checks', 'checks_import_only'))
    imported = run_import_job(worker, master.targets['import/sample/checks/1'].job)
    assert {piece.path.path for piece in payloads(worker, imported)} == {('subject',), ('checks',)}
    assert handle(master, imported).state.name == 'RESOLVED'
    expected = {'sample:subject': {'declare:value': 'declared', 'call:value': 'import only'}}
    assert accepted(master) == expected
    tested = run_test_job(worker, master.targets['test/sample/checks/test_ok/0'].job)
    # A cached test module does not rerun its top-level call; the import result must keep that observation.
    assert {piece.key for piece in payloads(worker, tested)} == {'declare:value'}
    assert handle(master, tested).state.name == 'RESOLVED'
    assert accepted(master) == expected


def test_import_retry_rejects_new_code_requirements_from_tested_module(worker):
    master = make_master(worker, {
        'subject': 'subject_late_import', 'checks': 'checks_retry', 'other': 'subject',
        })
    handle(master, run_import(worker, 'subject', 'subject_late_import'))
    handle(master, run_import(worker, 'checks', 'checks_retry'))
    handle(master, run_import(worker, 'other', 'subject'))
    result = run_import_job(worker, master.targets['import/sample/checks/1'].job)
    assert isinstance(result, worker.imports.htypes.import_job.incomplete_result)
    assert result.tested_requirements
    target = handle(master, result)
    assert target.state.name == 'FAILED'
    assert 'uses code.other.value when the test module is imported' in target.error
    assert 'but not when it is imported' in target.error


def test_failed_import_retry_replays_declarations_but_not_observations(worker):
    cfg = config_for_tests(worker, {'subject': recorded_module(worker, 'subject')})
    failed = run_import(worker, 'checks', 'checks_failed', cfg_items=cfg)
    assert isinstance(failed, worker.imports.htypes.import_job.failed_result)
    succeeded = run_import(worker, 'checks', cfg_items=cfg)
    assert values(worker, succeeded) == {('sample:subject', 'declare:value'): 'declared'}
    tested = run_test(worker, cfg_items=cfg)
    assert values(worker, tested) == {
        ('sample:subject', 'declare:value'): 'declared',
        ('sample:subject', 'call:value'): 'ok',
        }


def test_changed_source_does_not_replay_old_declarations(worker):
    original = run_import(worker, 'subject')
    assert run_import(worker, 'subject').constructors == original.constructors
    changed = run_import(worker, 'subject', 'subject_changed')
    assert values(worker, changed) == {('sample:subject', 'declare:changed'): 'declared'}


def test_identical_source_keeps_provider_identity(worker):
    run_import(worker, 'subject')
    other = run_import(worker, 'other', 'subject')
    assert values(worker, other) == {('sample:other', 'declare:value'): 'declared'}


def test_changed_import_config_does_not_replay_old_declarations(worker, monkeypatch):
    original = run_import(worker, 'subject')
    support = worker.animate('rc_test:test_constructors:test_constructors.module')
    original_init = support.TestConstructor.__init__

    def init(self, provider, key, value):
        original_init(self, provider, key, 'new configuration')

    monkeypatch.setattr(support.TestConstructor, '__init__', init)
    cfg = config_for_tests(worker, {'unused': recorded_module(worker, 'unused')})
    changed = run_import(worker, 'subject', cfg_items=cfg)
    assert values(worker, changed) == {('sample:subject', 'declare:value'): 'new configuration'}
    assert run_import(worker, 'subject').constructors == original.constructors


def test_cached_test_module_probes_do_not_publish_own_constructors(worker):
    master = make_master(worker, {'subject': 'unused', 'checks': 'checks_marked'})
    imported = run_import(worker, 'checks', 'checks_marked')
    target = handle(master, imported)
    assert target.module_tgt is None
    assert accepted(master) == {}
    handle(master, run_import(worker, 'subject', 'unused'))
    assert target.module.is_test
    assert accepted(master) == {}
    # Same source and recorder as the import job, so this executes the cached test-module probe.
    assert run_test(worker, source_name='checks_marked').constructors == ()


def test_collector_subsystems_released_with_declarations_cached(worker, monkeypatch, caplog):
    collector = worker.imports.code.ctr_collector
    refs = []
    original = collector.CtrCollector.__init__

    def init(self, context, *args):
        original(self, context, *args)
        refs.extend([weakref.ref(self), weakref.ref(context)])

    monkeypatch.setattr(collector.CtrCollector, '__init__', init)
    factory = worker.subsystem_factory

    def subsystem(**kw):
        system = factory(**kw)
        refs.append(weakref.ref(system))
        return system

    worker.subsystem_factory = subsystem
    cfg = config_for_tests(worker, {'subject': recorded_module(worker, 'subject')})
    with caplog.at_level(logging.CRITICAL):
        first = run_import(worker, 'subject')
        run_test(worker, 'test_fail', cfg_items=cfg)
        run_test(worker, cfg_items=cfg)
        again = run_import(worker, 'subject')
    assert again.constructors == first.constructors
    gc.collect()
    assert refs and all(ref() is None for ref in refs)
