from functools import wraps
from inspect import isfunction as test_imported
from builtins import len as test_builtin

from .code.base.mark import mark
from .code import unresolved as test_unresolved


def ordinary(fn):
    @wraps(fn)
    def wrapped(*args, **kw):
        return fn(*args, **kw)
    return wrapped


@mark.test.wrapper
@ordinary
@mark.test.wrapper
def test_sync():
    pass


@ordinary
@mark.test.wrapper
async def test_async():
    pass


@mark.test.wrapper
@ordinary
def test_generator():
    yield
    raise RuntimeError('generator exhausted')


@ordinary
@mark.test.wrapper
async def test_async_generator():
    yield
    raise RuntimeError('async generator exhausted')


@mark.test.wrapper
def test_incomplete():
    from .code import missing
    missing.fn()


@mark.test.wrapper
def test_signature(first, /, second=1, *, third=2):
    pass
