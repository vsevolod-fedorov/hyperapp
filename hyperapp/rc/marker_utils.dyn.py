import inspect

from .code.probe import real_fn, check_method_decorator_order


def check_is_function(fn):
    fn = real_fn(fn)
    if not (inspect.isfunction(fn) or inspect.ismethod(fn) and inspect.isfunction(fn.__func__)):
        raise RuntimeError(
            f"Unknown object attempted to be marked: {fn!r};"
            " Expected function, classmethod or staticmethod")
    return fn
