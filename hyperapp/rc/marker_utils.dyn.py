import inspect


# Marker wrappers expose the function they wrap through this property. Follow it recursively so
# validation and discoveries always see the real function, not an arbitrary wrapper depth.
def real_fn(fn):
    while True:
        try:
            wrapped = fn.real_fn
        except AttributeError:
            return fn
        if wrapped is fn:
            return fn
        fn = wrapped


def check_not_classmethod(fn):
    if type(fn) is classmethod:
        raise RuntimeError(
            f"Classmethod {fn!r} is marked after @classmethod;"
            " place the marker before the @classmethod decorator")


def check_is_function(fn):
    fn = real_fn(fn)
    if not inspect.isfunction(fn):
        raise RuntimeError(
            f"Unknown object attempted to be marked: {fn!r};"
            " Expected function, classmethod or staticmethod")
    return fn
