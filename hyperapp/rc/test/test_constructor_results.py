from functools import partial

import pytest

from constructor_job_support import accepted, handle, make_master, path, run_import, run_import_job, run_test_job
from test_probe_jobs import worker


@pytest.fixture
def master(worker):
    master = make_master(worker, {'subject': 'subject', 'checks': 'checks'})
    handle(master, run_import(worker, 'subject'))
    handle(master, run_import(worker, 'checks'))
    return master


def _constructor_ref(worker, provider='subject', key='new', value='new'):
    support = worker.animate('rc_test:test_constructors:test_constructors.module')
    ctr = support.TestConstructor(path(worker, provider), key, value)
    return support.code.constructor.constructor_ref(ctr)


def _envelope(worker, payload):
    protocol = worker.animate('rc:constructor:constructor.module')
    return worker.svc.mosaic.put(protocol.htypes.constructor.constructor(
        path=path(worker, 'subject').piece, key='bad', payload=worker.svc.mosaic.put(payload)))


def _reject_batch(worker, master, bad, error_type, message):
    registry = master.targets.constructors
    decoder = master.system.animate(worker.piece('rc:rc_constructor_creg:rc_constructor_creg.service'))
    before = accepted(master)
    with pytest.raises(error_type, match=message):
        registry.prepare(
            decoder, (_constructor_ref(worker), bad), {path(worker, 'subject')},
            source_target='test/sample/checks/test_ok/0')
    assert accepted(master) == before


def test_registry_rejects_conflict_with_accepted_constructor(worker, master):
    bad = _constructor_ref(worker, key='declare:value', value='contradiction')
    _reject_batch(worker, master, bad, ValueError, "Conflicting constructor sample:subject: 'declare:value'")


def test_registry_rejects_conflict_within_batch(worker, master):
    bad = _constructor_ref(worker, value='contradiction')
    _reject_batch(worker, master, bad, ValueError, "Conflicting constructor sample:subject: 'new'")


def test_registry_rejects_malformed_envelope(worker, master):
    bad = worker.svc.mosaic.put(path(worker, 'subject').piece)
    _reject_batch(worker, master, bad, TypeError, 'Invalid constructor envelope')


def test_registry_rejects_unexpected_provider(worker, master):
    bad = _constructor_ref(worker, provider='outsider')
    _reject_batch(worker, master, bad, ValueError, 'unexpected provider sample:outsider')


def test_registry_rejects_missing_decoder(worker, master):
    bad = _envelope(worker, path(worker, 'subject').piece)
    _reject_batch(worker, master, bad, KeyError, 'path')


def test_registry_rejects_payload_owner_mismatch(worker, master):
    support = worker.animate('rc_test:test_constructors:test_constructors.module')
    payload = support.TestConstructor(path(worker, 'outsider'), 'bad', 'bad').piece
    _reject_batch(worker, master, _envelope(worker, payload), ValueError, 'ownership/key mismatch')


def _unexpected_provider_batch(worker):
    return (_constructor_ref(worker), _constructor_ref(worker, provider='outsider'))


def _assert_target_rejects_batch(master, result, message='unexpected provider sample:outsider'):
    before = accepted(master)
    target_names = {target.name for target in master.targets}
    target = handle(master, result)
    assert target.state.name == 'FAILED'
    assert message in target.error
    assert accepted(master) == before
    assert {target.name for target in master.targets} == target_names
    return target


def test_import_handler_rejects_whole_batch(worker, master):
    result = worker.imports.htypes.import_job.succeeded_result(
        target='import/sample/subject/0', requirements=(), tested_requirements=(), test_functions=(),
        constructors=_unexpected_provider_batch(worker))
    _assert_target_rejects_batch(master, result)


def test_import_retry_handler_rejects_whole_batch(worker):
    master = make_master(worker, {'subject': 'subject', 'checks': 'checks_retry'})
    handle(master, run_import(worker, 'subject'))
    handle(master, run_import(worker, 'checks', 'checks_retry'))
    result = worker.imports.htypes.import_job.succeeded_result(
        target='import/sample/checks/1', requirements=(), tested_requirements=(), test_functions=(),
        constructors=_unexpected_provider_batch(worker))
    _assert_target_rejects_batch(master, result)


def test_test_handler_rejects_whole_batch(worker, master):
    result = worker.tests.htypes.test_job.succeeded_result(
        target='test/sample/checks/test_ok/0', tested_requirements=(),
        constructors=_unexpected_provider_batch(worker))
    _assert_target_rejects_batch(master, result)


def test_invalid_first_batch_does_not_attach_module_or_tests(worker):
    master = make_master(worker, {'subject': 'subject_with_test'})
    imported = run_import(worker, 'subject', 'subject_with_test')
    malformed = worker.svc.mosaic.put(path(worker, 'subject').piece)
    result = worker.imports.htypes.import_job.succeeded_result(
        target=imported.target,
        requirements=imported.requirements,
        tested_requirements=imported.tested_requirements,
        test_functions=imported.test_functions,
        constructors=(*imported.constructors, malformed),
        )
    target = handle(master, result)
    assert target.state.name == 'FAILED'
    assert target.module_tgt is None
    assert accepted(master) == {}
    assert not any(tgt.name.startswith(('module/compiled/', 'test/')) for tgt in master.targets)


def _import_result_factory(worker, result):
    return partial(
        worker.imports.htypes.import_job.succeeded_result,
        target=result.target, requirements=result.requirements, tested_requirements=result.tested_requirements,
        test_functions=result.test_functions)


def _first_import(worker):
    master = make_master(worker, {'subject': 'subject_with_test'})
    result = run_import(worker, 'subject', 'subject_with_test')
    return master, _import_result_factory(worker, result)


def _import_retry(worker):
    master = make_master(worker, {'subject': 'subject', 'checks': 'checks_retry'})
    handle(master, run_import(worker, 'subject'))
    handle(master, run_import(worker, 'checks', 'checks_retry'))
    result = run_import_job(worker, master.targets['import/sample/checks/1'].job)
    return master, _import_result_factory(worker, result)


def _test_run(worker):
    master = make_master(worker, {'subject': 'subject', 'checks': 'checks'})
    handle(master, run_import(worker, 'subject'))
    handle(master, run_import(worker, 'checks'))
    result = run_test_job(worker, master.targets['test/sample/checks/test_ok/0'].job)
    return master, partial(
        worker.tests.htypes.test_job.succeeded_result,
        target=result.target, tested_requirements=result.tested_requirements)


@pytest.fixture(params=[_first_import, _import_retry, _test_run])
def successful_result(request, worker):
    return request.param(worker)


def test_handler_reports_empty_decoder_exception(worker, successful_result):
    master, make_result = successful_result
    support = worker.animate('rc_test:test_constructors:test_constructors.module')
    decoder = master.system.animate(worker.piece('rc:rc_constructor_creg:rc_constructor_creg.service'))

    def decode(piece):
        if piece.key == 'bad':
            raise AssertionError()
        return support.TestConstructor.from_piece(piece)

    decoder.update_resolved_config({support.htypes.test_constructors.constructor: decode})
    result = make_result(constructors=(_constructor_ref(worker), _constructor_ref(worker, key='bad')))
    target = _assert_target_rejects_batch(master, result, 'AssertionError')
    assert "sample:subject: 'bad'" in target.error
    assert result.target in target.error


def test_handler_rejects_decoder_round_trip_mismatch(worker, successful_result):
    master, make_result = successful_result
    support = worker.animate('rc_test:test_constructors:test_constructors.module')
    decoder = master.system.animate(worker.piece('rc:rc_constructor_creg:rc_constructor_creg.service'))

    def decode(piece):
        ctr = support.TestConstructor.from_piece(piece)
        if piece.key == 'bad':
            ctr.value = 'changed during reconstruction'
        return ctr

    decoder.update_resolved_config({support.htypes.test_constructors.constructor: decode})
    result = make_result(constructors=(_constructor_ref(worker), _constructor_ref(worker, key='bad')))
    target = _assert_target_rejects_batch(master, result, "Constructor round trip mismatch for sample:subject: 'bad'")
    assert result.target in target.error


def test_import_retry_conflict_reports_original_job(worker):
    master, make_result = _import_retry(worker)
    bad = _constructor_ref(worker, key='declare:value', value='contradiction')
    result = make_result(constructors=(_constructor_ref(worker), bad))
    target = _assert_target_rejects_batch(master, result, "Conflicting constructor sample:subject: 'declare:value'")
    assert result.target in target.error
    assert 'previous discovery from import/sample/subject/0' in target.error


def test_test_conflict_preserves_first_successful_origin(worker):
    master = make_master(worker, {'subject': 'subject', 'checks': 'checks_conflict'})
    handle(master, run_import(worker, 'subject'))
    handle(master, run_import(worker, 'checks', 'checks_conflict'))
    first = run_test_job(worker, master.targets['test/sample/checks/test_first/0'].job)
    assert handle(master, first).state.name == 'RESOLVED'
    original = master.targets['module/compiled/sample/subject'].constructors
    repeat = run_test_job(worker, master.targets['test/sample/checks/test_repeat/0'].job)
    assert handle(master, repeat).state.name == 'RESOLVED'
    rediscovered = master.targets['module/compiled/sample/subject'].constructors
    assert len(original) == len(rediscovered)
    assert all(a is b for a, b in zip(original, rediscovered))

    conflict = run_test_job(worker, master.targets['test/sample/checks/test_conflict/0'].job)
    result = worker.tests.htypes.test_job.succeeded_result(
        target=conflict.target, tested_requirements=conflict.tested_requirements,
        constructors=(_constructor_ref(worker), *conflict.constructors))
    target = _assert_target_rejects_batch(master, result, "Conflicting constructor sample:subject: 'call:value'")
    assert result.target in target.error
    assert f'previous discovery from {first.target}' in target.error
    assert repeat.target not in target.error


def test_accepted_payloads_remain_the_validated_snapshot(worker, master):
    registry = master.targets.constructors
    before = registry.pieces
    ctr, = registry.for_path(path(worker, 'subject'))
    ctr.value = 'changed after acceptance'
    assert registry.pieces == before
