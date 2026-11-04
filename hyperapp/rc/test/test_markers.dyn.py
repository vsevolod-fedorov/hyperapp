import inspect

from .code.marker_utils import check_is_function, check_method_decorator_order
from .code.path import Path


class TestService:

    def __init__(self):
        self.calls = []


def test_service():
    return TestService()


def _decorate(fn, path, test_service, marker_name, args, kw):
    check_method_decorator_order(fn)
    real_fn = check_is_function(fn)
    if not isinstance(path, Path):
        raise RuntimeError(f"Wrong provider path: {path!r}")
    if not isinstance(test_service, TestService):
        raise RuntimeError(f"Wrong injected service: {test_service!r}")
    test_service.calls.append((marker_name, str(path), real_fn.__name__))
    real_fn.test_marker = marker_name
    real_fn.provider_path = path
    real_fn.injected_service = test_service
    real_fn.marker_args = args
    real_fn.marker_kw = kw
    return fn


def _is_bare_decoration(args, kw):
    return len(args) == 1 and not kw and inspect.isfunction(args[0])


class ClassMarker:

    def __init__(self, path, test_service):
        self._path = path
        self._test_service = test_service

    def __call__(self, *args, **kw):
        if _is_bare_decoration(args, kw):
            return _decorate(args[0], self._path, self._test_service, 'class', (), {})
        def decorator(fn):
            return _decorate(fn, self._path, self._test_service, 'class', args, kw)
        return decorator


def function_marker(*args, path, test_service, **kw):
    if _is_bare_decoration(args, kw):
        return _decorate(args[0], path, test_service, 'function', (), {})
    def decorator(fn):
        return _decorate(fn, path, test_service, 'function', args, kw)
    return decorator
