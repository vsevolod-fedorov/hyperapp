from . import services
from .code.base.mark import mark


@mark.test.constructor
def import_only():
    assert services.mosaic is not None
    return other.value()


@mark.test.constructor
def f0():
    return 'ok'


@mark.test.constructor
def f1():
    return 'ok'


@mark.test.constructor
def f2():
    return 'ok'


@mark.test.constructor
def f3():
    return 'ok'


# Resolve the marker before discovering this import; the subject's own import must not wait for
# other's completed module, which waits for these tests. Tests supply its recorded module instead.
from .code import other
