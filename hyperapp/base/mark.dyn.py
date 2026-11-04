import sys
from contextlib import contextmanager

from hyperapp.boot.htypes import Type


_active = None


class _Activation:

    def __init__(self, registry, module_to_path):
        self.registry = registry
        self.module_to_path = module_to_path


class _Mark:

    def __init__(self, path=()):
        self._path = path

    def __getattr__(self, name):
        if name.startswith('_'):
            raise AttributeError(name)
        return _Mark((*self._path, name))

    def __call__(self, *args, **kw):
        if _active is not None:
            try:
                provider_path = _active.module_to_path[_caller_module_name()]
            except KeyError:
                # This job did not activate the calling module; use the no-op argument handling below.
                pass
            else:
                # Active markers handle both bare decoration and parameterized decorator factories.
                marker = _active.registry.make_marker(self._path, provider_path)
                return marker(*args, **kw)
        # Bare decoration (@mark.foo): the decorated callable is the sole argument; return it unchanged.
        # Types are callable too, but like strings they are decorator parameters here, not bare callables.
        if (
                len(args) == 1 and not kw and callable(args[0])
                and not isinstance(args[0], (Type, str))
                ):
            return args[0]
        # Parameterized decoration (@mark.foo(...)): the decorated callable arrives on the next call.
        return _noop_decorator


def _caller_module_name():
    return sys._getframe(2).f_globals.get('__name__')


def _noop_decorator(fn):
    return fn


mark = _Mark()


# Only recorded modules selected by the running job get real markers. Other modules animated by that
# job keep the no-op behavior, so they can not repeat discoveries made by their own import jobs.
@contextmanager
def markers_activated(registry, module_to_path):
    global _active
    if _active is not None:
        active_names = ', '.join(sorted(_active.module_to_path))
        raise RuntimeError(f"Markers are already active for: {active_names}")
    _active = _Activation(registry, module_to_path)
    try:
        yield
    finally:
        _active = None
