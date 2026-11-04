import inspect
import types

from .code.path import Path


_active_context = None
_MISSING = object()


# Follow both protocols in one traversal: ordinary decorators can surround probes and vice versa.
# Unwrap the descriptor's function first, then preserve its receiver (including class receivers).
def real_fn(fn):
    seen = {}
    receiver = None
    while True:
        if id(fn) in seen:
            raise ValueError("Wrapper cycle while finding real function")
        # Properties can return temporary bound methods. Keep them alive so their ids cannot be reused.
        seen[id(fn)] = fn
        if inspect.ismethod(fn):
            receiver = fn.__self__
            fn = fn.__func__
            continue
        # Unbound method decorators must remain visible to decorator-order validation.
        # Only a bound method has a receiver we can preserve while unwrapping.
        if isinstance(fn, (classmethod, staticmethod)):
            return fn
        wrapped = _wrapper_attr(fn, 'real_fn')
        if wrapped is _MISSING:
            wrapped = _wrapper_attr(fn, '__wrapped__')
        if wrapped is _MISSING:
            if receiver is not None:
                return types.MethodType(fn, receiver)
            return fn
        fn = wrapped


# Proxies (including unresolved imports) synthesize arbitrary attributes. Introspection must
# not resolve them or mistake those synthesized objects for an endless chain of wrappers.
def _wrapper_attr(fn, name):
    # Missing attributes terminate traversal; a self-reference must instead reach the cycle check.
    if inspect.getattr_static(fn, name, _MISSING) is _MISSING:
        return _MISSING
    return getattr(fn, name)


def check_method_decorator_order(fn):
    fn = real_fn(fn)
    for decorator in (classmethod, staticmethod):
        if isinstance(fn, decorator):
            raise RuntimeError(
                f"@{decorator.__name__} must be outside marker and probe decorators")


class DiscoverySink:

    def __init__(self):
        self._entries = []
        self._closed = False

    @property
    def entries(self):
        return tuple(self._entries)

    def add(self, entry):
        if self._closed:
            raise RuntimeError("Discovery sink is closed")
        self._entries.append(entry)

    def close(self):
        self._entries.clear()
        self._closed = True


class ProbeContext:

    def __init__(self):
        self.discoveries = DiscoverySink()
        self._states = {}
        self._resolve_service = None
        self._closed = False

    def __enter__(self):
        global _active_context
        if _active_context is not None:
            raise RuntimeError("A probe context is already active")
        if self._closed:
            raise RuntimeError("Probe context is closed")
        _active_context = self
        return self

    def __exit__(self, exc_type, exc, tb):
        global _active_context
        _active_context = None
        self._resolve_service = None
        # Clear dictionaries in place too: a resolver may have kept a reference to its state.
        for probe, state in self._states.values():
            state.clear()
        self._states.clear()
        self.discoveries.close()
        self._closed = True

    def bind_services(self, resolve_service):
        if _active_context is not self:
            raise RuntimeError("Probe context is not active")
        if self._resolve_service is not None:
            raise RuntimeError("Probe context services are already bound")
        self._resolve_service = resolve_service

    # Cached probes keep a resource reference, not an injected instance or a bound resolver.
    # The resolver is job-owned; service names and inference remain the concrete probe's concern.
    def invite(self, service_ref):
        if _active_context is not self:
            raise RuntimeError("Probe context is not active")
        if self._resolve_service is None:
            raise RuntimeError("Probe context services are not bound")
        return self._resolve_service(service_ref)

    def state_for(self, probe):
        if _active_context is not self:
            raise RuntimeError("Probe context is not active")
        # Identity keys avoid executing proxy equality/hash. Holding the probe prevents id reuse
        # within a job; exit drops both it and any resolved values or callbacks.
        return self._states.setdefault(id(probe), (probe, {}))[1]


class ProbeBase:

    def __init__(self, path, fn):
        if not isinstance(path, Path):
            raise TypeError(f"Probe provider must be rc.path.Path: {path!r}")
        # The outer method decorator must control binding instead of receiving an extra instance.
        check_method_decorator_order(fn)
        self._path = path
        self._fn = fn

    def __get__(self, obj, owner=None):
        if obj is None:
            return self
        return types.MethodType(self, obj)

    def __call__(self, *args, **kw):
        return self._fn(*args, **kw)

    @property
    def path(self):
        return self._path

    @property
    def __wrapped__(self):
        return self._fn

    @property
    def context(self):
        # Cached modules keep only the wrapper, never a job reference. Looking up on use rebinds
        # even probes in modules not animated again; clearing the slot detaches them all at exit.
        if _active_context is None:
            raise RuntimeError("No active probe context")
        return _active_context

    @property
    def state(self):
        return self.context.state_for(self)
