import gc
import logging
import weakref
from pathlib import Path
from types import SimpleNamespace

import pytest

from hyperapp.boot.boot import boot_services, load_projects_resources, parse_path


TEST_DIR = Path(__file__).parent.resolve()
PROGRAMS = TEST_DIR / 'resources' / 'probe_jobs'


def _source(name):
    return (PROGRAMS / f'{name}.dyn.py').read_text()


# Use the real resource loader, worker config and job entry points. Only transport is a local
# result collector, and the test worker layer supplies the small probe's resolver.
@pytest.fixture
def worker():
    svc = boot_services()
    resources = load_projects_resources(
        svc.pyobj_creg, svc.mosaic, svc.source_path, svc.builtin_name_to_type,
        svc.builtin_name_to_service, svc.resource_type_producer, TEST_DIR / 'projects.yaml')

    def piece(path):
        return resources[parse_path(path)]

    def animate(path):
        return svc.pyobj_creg.animate(piece(path))

    system = animate('base:system/system:system.module').setup_system([
        piece('base:config:config'),
        piece('rc:job/worker_config:config'),
        piece('rc_test:worker_config:config'),
        ])
    return SimpleNamespace(
        svc=svc, piece=piece, animate=animate,
        imports=animate('rc:job/import:import.module'),
        tests=animate('rc:job/test:test.module'),
        probe=animate('rc:probe:probe.module'),
        recorder=animate('rc:import_recorder:import_recorder.module'),
        support=animate('rc_test:test_probes:test_probes.module'),
        system=system,
        registry=system.animate(piece('rc:job/marker_registry:marker_registry.service')),
        import_to_req=system.animate(piece('rc:job/import_to_req:import_to_req.service')),
        subsystem_factory=system.animate(piece('base:system/system:subsystem_factory.service')),
        )


def _cfg_items(worker):
    item = worker.recorder.htypes.import_recorder.import_cfg_item(
        import_path=('code', 'base', 'mark'),
        resource=worker.svc.mosaic.put(worker.piece('base:mark:mark.module')),
        )
    return (worker.svc.mosaic.put(item),)


def _run(worker, kind, source, function=None):
    path = worker.probe.code.path.Path('sample', ('subject',))
    job_type = worker.animate(f'rc:job/{kind}.t:{kind}_job')
    args = dict(target='job', path=path.piece, source=source, cfg_items=_cfg_items(worker))
    if function is not None:
        args['function'] = function
    job = job_type(**args)
    results = []

    def send_message(remote_peer, local_identity, result):
        # The transport boundary must already be outside both scopes, including error results.
        assert worker.probe._active_context is None
        assert worker.imports.code.context.code.mark._active is None
        results.append(result)

    module = worker.imports if kind == 'import' else worker.tests
    getattr(module, f'run_{kind}_job')(
        job, SimpleNamespace(remote_peer=None, local_identity=None),
        worker.import_to_req, worker.registry, worker.subsystem_factory,
        SimpleNamespace(send_message=send_message))
    assert len(results) == 1
    return results[0]


def _observe(worker, monkeypatch):
    observations = []
    original = worker.support.Resolver.__call__

    def resolve(resolver, probe):
        value = original(resolver, probe)
        observations.append((probe, probe.context, probe.state, value, resolver))
        return value

    monkeypatch.setattr(worker.support.Resolver, '__call__', resolve)
    return observations


def _check_detached(worker, observations):
    assert observations
    for probe, context, state, value, resolver in observations:
        assert state == {}
        assert context.discoveries.entries == ()
        assert context._resolve_service is None
        with pytest.raises(RuntimeError, match='not active'):
            context.invite(worker.support.RESOLVER_REF)
        with pytest.raises(RuntimeError, match='No active probe context'):
            probe.context
        with pytest.raises(RuntimeError, match='closed'):
            context.discoveries.add('late')
    assert worker.registry._resolve_service is None


@pytest.mark.parametrize('program,outcome,expected_error', [
    ('import_succeeded', 'succeeded', None),
    ('import_failed', 'failed', 'expected failure'),
    ('import_incomplete', 'incomplete', None),
    ('import_wrapper_cycle', 'failed', 'Wrapper cycle'),
    ('import_wrapper_self_cycle', 'failed', 'Wrapper cycle'),
    ])
def test_import_job_cleans_discoveries_and_bindings(worker, monkeypatch, program, outcome, expected_error):
    observations = _observe(worker, monkeypatch)
    result = _run(worker, 'import', _source(program))
    assert isinstance(result, worker.animate(f'rc:job/import.t:{outcome}_result'))
    if expected_error is not None:
        assert expected_error in result.error
    _check_detached(worker, observations)


@pytest.mark.parametrize('decorator', ['classmethod', 'staticmethod'])
def test_import_job_rejects_inner_method_decorators(worker, decorator):
    result = _run(worker, 'import', _source(f'inner_{decorator}'))
    assert isinstance(result, worker.imports.htypes.import_job.failed_result)
    assert f'@{decorator} must be outside' in result.error


def test_cached_wrapped_tests_metadata_execution_and_job_exit(worker, monkeypatch):
    observations = _observe(worker, monkeypatch)
    source = _source('wrapped_tests')
    imported = _run(worker, 'import', source)
    assert isinstance(imported, worker.imports.htypes.import_job.succeeded_result)
    functions = {fn.name: fn for fn in imported.test_functions}
    assert set(functions) == {
        'test_sync', 'test_async', 'test_generator', 'test_async_generator',
        'test_incomplete', 'test_signature',
        }
    assert functions['test_signature'].params == ('first', 'second', 'third')
    for name, is_async, is_generator, outcome in [
            ('test_sync', False, False, 'succeeded'),
            ('test_async', True, False, 'succeeded'),
            ('test_generator', False, True, 'failed'),
            ('test_async_generator', True, True, 'failed'),
            ('test_incomplete', False, False, 'incomplete'),
            ('test_sync', False, False, 'succeeded'),
            ]:
        function = functions[name]
        assert (function.is_async, function.is_generator) == (is_async, is_generator)
        before = len(observations)
        result = _run(worker, 'test', source, function)
        assert isinstance(result, worker.animate(f'rc:job/test.t:{outcome}_result'))
        # These are the very same recorded modules as the import job: wrappers must execute,
        # rather than discovery accidentally replacing them with their real functions.
        assert len(observations) > before
        _check_detached(worker, observations)
        if is_generator:
            assert 'generator exhausted' in result.error
    first_probe, first_context, _, first_value, first_resolver = observations[0]
    last_probe, last_context, _, last_value, last_resolver = observations[-2]
    assert first_probe is last_probe
    assert first_context is not last_context
    assert first_value is not last_value
    assert first_resolver is not last_resolver
    assert first_resolver.state is not last_resolver.state
    assert first_resolver.registry is not last_resolver.registry


def test_marker_binding_is_by_service_reference_and_is_detached(worker):
    service_ref = worker.svc.mosaic.put(worker.piece('rc:probe:probe_context.service'))
    path = worker.probe.code.path.Path('sample', ('subject',))
    with worker.imports.code.context.job_active(worker.subsystem_factory, worker.registry, {}) as context:
        with worker.registry.bound(context.invite) as bound:
            # The actor names the parameter 'context', not 'probe_context'. Resolver is still
            # constructed from test worker declarations in the fresh job subsystem.
            marker = bound.make_marker(('test', 'wrapper'), path)
            probe = marker(lambda: 42)
            assert probe.context is context
            assert context.invite(service_ref) is context
            resolver = context.invite(worker.support.RESOLVER_REF)
            assert resolver.context is context
            assert probe.path is path
            assert probe() == 42
            with pytest.raises(RuntimeError, match="Unknown marker 'test.wrapper.extra'"):
                bound.make_marker(('test', 'wrapper', 'extra'), path)
    assert bound._resolve_service is None
    assert worker.registry._resolve_service is None
    with pytest.raises(RuntimeError, match='no active job binding'):
        bound.make_marker(('test', 'wrapper'), path)


@pytest.fixture
def mutated_worker_services(worker, monkeypatch):
    state_piece = worker.piece('rc_test:test_probes:state.service')
    registry_piece = worker.piece('rc_test:test_probes:registry.service')
    worker_state = worker.system.animate(state_piece)
    worker_registry = worker.system.animate(registry_piece)
    config_creg = worker.system.animate(worker.piece('base:system/system:service_config_creg.service'))
    worker_config = config_creg.animate(registry_piece).config
    key = worker.support.htypes.builtin.imports
    declaration = worker.piece('rc_test:test_probes:registry_value.actor')
    assert worker_config[key] == declaration
    # Both live configuration and already-resolved objects in the outer subsystem are dirty.
    worker_state.calls.append('worker mutation')
    worker_config[key] = 'worker config mutation'
    worker_registry.update_config({key: 'worker registry mutation'})
    job_resolvers = []
    original = worker.support.Resolver.__call__

    def resolve(resolver, probe):
        assert resolver.state.calls == []
        assert resolver.registry._unresolved_config[key] == declaration
        assert resolver.state is not worker_state
        assert resolver.registry is not worker_registry
        result = original(resolver, probe)
        job_resolvers.append(resolver)
        resolver.state.calls.append('job mutation')
        resolver.registry.update_config({key: 'job registry mutation'})
        return result

    monkeypatch.setattr(worker.support.Resolver, '__call__', resolve)
    return SimpleNamespace(
        state=worker_state, registry=worker_registry, config=worker_config,
        key=key, job_resolvers=job_resolvers,
        )


def _check_job_services_isolated(services):
    first, second = services.job_resolvers
    assert first is not second
    assert first.state is not second.state
    assert first.registry is not second.registry
    assert first.context is not second.context
    assert services.state.calls == ['worker mutation']
    assert services.config[services.key] == 'worker registry mutation'
    assert services.registry._unresolved_config[services.key] == 'worker registry mutation'


@pytest.mark.parametrize('program,outcome', [
    ('import_succeeded', 'succeeded'),
    ('import_failed', 'failed'),
    ('import_incomplete', 'incomplete'),
    ])
def test_import_job_services_and_registry_mutations_are_isolated(worker, mutated_worker_services, program, outcome):
    result = _run(worker, 'import', _source(program))
    assert isinstance(result, worker.animate(f'rc:job/import.t:{outcome}_result'))
    # Different source makes the next import execute instead of reusing the cached module.
    result = _run(worker, 'import', _source('import_next'))
    assert isinstance(result, worker.imports.htypes.import_job.succeeded_result)
    _check_job_services_isolated(mutated_worker_services)


@pytest.mark.parametrize('function,outcome', [
    ('test_succeeded', 'succeeded'),
    ('test_failed', 'failed'),
    ('test_incomplete', 'incomplete'),
    ])
def test_test_job_services_and_registry_mutations_are_isolated(worker, mutated_worker_services, function, outcome):
    source = _source('isolation_tests')
    imported = _run(worker, 'import', source)
    assert isinstance(imported, worker.imports.htypes.import_job.succeeded_result)
    functions = {fn.name: fn for fn in imported.test_functions}
    result = _run(worker, 'test', source, functions[function])
    assert isinstance(result, worker.animate(f'rc:job/test.t:{outcome}_result'))
    result = _run(worker, 'test', source, functions['test_next'])
    assert isinstance(result, worker.tests.htypes.test_job.succeeded_result)
    _check_job_services_isolated(mutated_worker_services)


def test_job_subsystems_are_released_while_probes_remain_cached(worker, monkeypatch, caplog):
    source = _source('wrapped_tests')
    refs = []
    original = worker.support.Resolver.__init__

    def init(resolver, context, state, registry):
        original(resolver, context, state, registry)
        refs.extend(weakref.ref(obj) for obj in (resolver, context, state, registry, registry._service_creg))

    monkeypatch.setattr(worker.support.Resolver, '__init__', init)
    # LogRecord arguments otherwise keep animated service objects alive in pytest's capture handlers.
    with caplog.at_level(logging.CRITICAL):
        imported = _run(worker, 'import', source)
        for fn in imported.test_functions:
            if fn.name != 'test_signature':
                _run(worker, 'test', source, fn)
    assert refs
    gc.collect()
    assert all(ref() is None for ref in refs)
    # The module is still in the real pyobj cache, including the original wrapped test functions.
    path = worker.probe.code.path.Path('sample', ('subject',))
    cfg_items = [worker.imports.web.summon(ref) for ref in _cfg_items(worker)]
    recorder = worker.recorder.import_recorder_piece(path.piece, cfg_items)
    piece = worker.recorder.recorded_python_module('subject', source, recorder)
    module = worker.svc.pyobj_creg.animate(piece)
    assert isinstance(module.test_sync, worker.support.TestProbe)
    with pytest.raises(RuntimeError, match='No active probe context'):
        module.test_sync.context


def test_worker_cache_is_not_a_job_service_fallback(worker):
    piece = worker.piece('base:system/system:config_creg.service')
    worker_only = object()
    worker.system.add_to_cache(piece, worker_only)
    with worker.imports.code.context.job_active(worker.subsystem_factory, worker.registry, {}) as context:
        with pytest.raises(KeyError):
            context.invite(worker.svc.mosaic.put(piece))
    assert worker.system.animate(piece) is worker_only
