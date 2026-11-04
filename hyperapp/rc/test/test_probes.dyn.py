from . import htypes
from .services import (
    mosaic,
    )
from .code.probe import ProbeBase, real_fn
from .data import resolver_service


RESOLVER_REF = mosaic.put(resolver_service)


class State:

    def __init__(self):
        self.calls = []


def state():
    return State()


def registry(system_code_registry_factory, config):
    return system_code_registry_factory('test_probe_registry', config)


def registry_value(piece, context, state):
    return context, state


# This resolver deliberately knows nothing about service signatures or object/factory inference.
# Direct and registry-mediated dependencies must resolve through the same current-job subsystem.
class Resolver:

    def __init__(self, context, state, registry):
        self.context = context
        self.state = state
        self.registry = registry

    def __call__(self, probe):
        assert self.context is probe.context
        context, state = self.registry.animate(htypes.builtin.imports(pyobj=(), raw=()))
        assert context is self.context
        assert state is self.state
        self.state.calls.append(probe.path)
        return object()


def resolver(context, state, registry):
    return Resolver(context, state, registry)


class TestProbe(ProbeBase):

    def __call__(self, *args, **kw):
        state = self.state
        if 'value' not in state:
            value = self.context.invite(RESOLVER_REF)(self)
            self.context.discoveries.add((self.path, real_fn(self).__name__))
            state['value'] = value
        # Wrapper execution is observable without altering the real function's signature or flags.
        state['calls'] = state.get('calls', 0) + 1
        return self._fn(*args, **kw)


def test_wrapper(fn, path, context, resolver):
    probe = TestProbe(path, fn)
    assert probe.context is context
    assert context.invite(RESOLVER_REF) is resolver
    return probe
