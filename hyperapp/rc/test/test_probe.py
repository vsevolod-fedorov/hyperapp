import gc
import inspect
import types
import weakref
from functools import wraps
from pathlib import Path

import pytest

from hyperapp.boot.boot import boot


TEST_DIR = Path(__file__).parent.resolve()


@pytest.fixture
def support():
    return boot(TEST_DIR / 'projects.yaml', 'rc_test:test_probes:test_probes.module')


@pytest.fixture
def module(support):
    return support.code.probe


@pytest.fixture
def path(module):
    return module.code.path.Path('sample', ('subject',))


class Wrapper:

    def __init__(self, fn):
        self.real_fn = fn

    def __call__(self, *args, **kw):
        return self.real_fn(*args, **kw)

    def __get__(self, obj, owner=None):
        return self if obj is None else types.MethodType(self, obj)


def ordinary_wrapper(fn):
    @wraps(fn)
    def wrapped(*args, **kw):
        return fn(*args, **kw)
    return wrapped


def test_real_fn_unwraps_interleaved_protocols(module, path):
    def fn(arg):
        return arg

    inner = module.ProbeBase(path, fn)
    outer = module.ProbeBase(path, ordinary_wrapper(Wrapper(inner)))
    assert inner.__wrapped__ is fn
    assert inspect.unwrap(inner) is fn
    assert inspect.signature(inner) == inspect.signature(fn)
    assert module.real_fn(outer) is fn
    wrapped = ordinary_wrapper(Wrapper(outer))
    assert module.real_fn(wrapped) is fn
    assert module.code.path.Path is type(outer.path)
    assert outer.path is path
    assert wrapped(42) == 42


@pytest.mark.parametrize('class_method', [False, True])
@pytest.mark.parametrize('outer_wrapper', [Wrapper, ordinary_wrapper, lambda fn: fn])
def test_real_fn_preserves_bound_receiver(module, path, class_method, outer_wrapper):
    class Sample:

        def method(receiver, value):
            return receiver, value

    original = Sample.method
    wrapped = outer_wrapper(module.ProbeBase(path, module.ProbeBase(path, original)))
    Sample.method = classmethod(wrapped) if class_method else wrapped
    sample = Sample()
    receiver = Sample if class_method else sample
    fn = module.real_fn(sample.method)
    assert fn.__func__ is original
    assert fn.__self__ is receiver
    assert tuple(inspect.signature(fn).parameters) == ('value',)
    assert sample.method(42) == (receiver, 42)


def test_real_fn_retains_temporary_bound_methods(module):
    methods = []

    class MethodWrapper:

        def __init__(self, receiver, name):
            self.receiver = receiver
            self.name = name

        @property
        def real_fn(self):
            # Check lifetime directly rather than relying on the allocator to reuse a method's id.
            assert all(ref() is not None for ref in methods)
            method = getattr(self.receiver, self.name)
            methods.append(weakref.ref(method))
            return method

        def __call__(self, *args, **kw):
            return self.real_fn(*args, **kw)

    class Sample:

        def original(self, value):
            return self, value

        def decorated(self, value):
            return self.original(value)

    sample = Sample()
    Sample.decorated.__wrapped__ = MethodWrapper(sample, 'original')
    fn = module.real_fn(MethodWrapper(sample, 'decorated'))
    assert fn.__func__ is Sample.original
    assert fn.__self__ is sample
    assert tuple(inspect.signature(fn).parameters) == ('value',)
    assert fn(42) == (sample, 42)
    assert all(ref() is None for ref in methods)


def test_staticmethod_and_class_access(module, path):
    def fn(value):
        return value

    class Sample:
        method = module.ProbeBase(path, fn)
        static = staticmethod(ordinary_wrapper(module.ProbeBase(path, module.ProbeBase(path, fn))))

    assert module.real_fn(Sample.method) is fn
    assert module.real_fn(Sample.static) is fn
    assert module.real_fn(Sample().static) is fn
    assert Sample.static(42) == 42
    assert Sample().static(42) == 42


@pytest.mark.parametrize('decorator', [classmethod, staticmethod])
@pytest.mark.parametrize('wrapper', [Wrapper, ordinary_wrapper, lambda fn: fn])
def test_probe_requires_outer_method_decorators(module, path, decorator, wrapper):
    descriptor = decorator(lambda: None)
    wrapped = wrapper(descriptor)
    assert module.real_fn(wrapped) is descriptor
    with pytest.raises(RuntimeError, match=f'@{decorator.__name__} must be outside'):
        module.ProbeBase(path, wrapped)


def test_wrapper_cycle_fails(module, path):
    wrapper = Wrapper(None)
    probe = module.ProbeBase(path, wrapper)
    wrapper.real_fn = probe
    with pytest.raises(ValueError, match='Wrapper cycle'):
        module.real_fn(probe)


@pytest.mark.parametrize('protocol', ['real_fn', '__wrapped__'])
def test_wrapper_self_cycle_fails(module, protocol):
    def fn():
        pass

    setattr(fn, protocol, fn)
    with pytest.raises(ValueError, match='Wrapper cycle'):
        module.real_fn(fn)


def test_provider_requires_path(module):
    with pytest.raises(TypeError, match='rc.path.Path'):
        module.ProbeBase('python.module.name', lambda: None)


def test_unwrapping_does_not_resolve_proxy_attributes(module):
    class Proxy:

        def __getattr__(self, name):
            raise AssertionError(f'Proxy attribute resolved: {name}')

    proxy = Proxy()
    assert module.real_fn(proxy) is proxy


@pytest.mark.parametrize('failure', [False, True])
def test_cached_probe_context_state_and_sink_are_job_local(support, module, path, failure):
    contexts = []
    values = []

    def resolve(probe):
        contexts.append(weakref.ref(probe.context))
        value = object()
        values.append(value)
        return value

    probe = support.TestProbe(path, lambda: 42)
    retained_states = []
    for index in range(2):
        context = module.ProbeContext()
        try:
            with context:
                context.bind_services({support.RESOLVER_REF: resolve}.__getitem__)
                assert probe.context is context
                assert probe() == probe() == 42
                assert probe.state['calls'] == 2
                assert probe.state['value'] is values[index]
                probe.state['callback'] = lambda ctx=context: ctx
                assert context.discoveries.entries == ((path, '<lambda>'),)
                retained_states.append(probe.state)
                if failure:
                    raise RuntimeError('failed job')
        except RuntimeError as error:
            assert str(error) == 'failed job'
        assert context.discoveries.entries == ()
        assert retained_states[-1] == {}
        with pytest.raises(RuntimeError, match='No active probe context'):
            probe.context
        with pytest.raises(RuntimeError, match='not active'):
            context.state_for(probe)
        with pytest.raises(RuntimeError, match='closed'):
            context.discoveries.add('late discovery')
        del context
        gc.collect()
        assert contexts[-1]() is None
    assert values[0] is not values[1]


def test_proxy_hash_and_equality_are_not_used(module, path):
    class Proxy(module.ProbeBase):

        def __hash__(self):
            raise AssertionError('probe hash executed')

        def __eq__(self, other):
            raise AssertionError('probe equality executed')

    probe = Proxy(path, lambda: None)
    other = Proxy(path, lambda: None)
    with module.ProbeContext():
        assert probe.state is probe.state
        assert probe.state is not other.state


def test_context_rejects_nesting_and_reentry(module):
    with module.ProbeContext() as context:
        with pytest.raises(RuntimeError, match='already active'):
            with module.ProbeContext():
                pass
        assert context.state_for(object()) == {}
    with pytest.raises(RuntimeError, match='closed'):
        with context:
            pass


def test_failed_resolver_does_not_cache_or_discover(support, module, path):
    def resolve(probe):
        raise RuntimeError('resolver failed')

    probe = support.TestProbe(path, lambda: None)
    with module.ProbeContext() as context:
        context.bind_services({support.RESOLVER_REF: resolve}.__getitem__)
        with pytest.raises(RuntimeError, match='resolver failed'):
            probe()
        assert probe.state == {}
        assert context.discoveries.entries == ()


def test_service_binding_is_scoped_to_current_context(module):
    ref = object()
    service = object()
    with module.ProbeContext() as first:
        first.bind_services({ref: service}.__getitem__)
        assert first.invite(ref) is service
        with pytest.raises(RuntimeError, match='already bound'):
            first.bind_services(lambda ref: None)
    with module.ProbeContext() as second:
        with pytest.raises(RuntimeError, match='not active'):
            first.invite(ref)
        with pytest.raises(RuntimeError, match='not bound'):
            second.invite(ref)
