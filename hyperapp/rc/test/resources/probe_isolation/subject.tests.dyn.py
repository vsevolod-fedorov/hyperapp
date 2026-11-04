from functools import wraps

from . import code
from .code.base.mark import mark
from .tested.code import subject


@mark.test.wrapper
def test_a_incomplete():
    assert subject.value() == 42
    assert code.late.value() == 43


@mark.test.wrapper
def test_b_failure():
    assert subject.value() == 42
    raise RuntimeError('expected test failure')


@mark.test.wrapper
def test_c_success():
    assert subject.value() == 42


@mark.test.wrapper
def test_generator():
    yield
    assert subject.value() == 42
    raise RuntimeError('generator exhausted')


@mark.test.wrapper
async def test_async_generator():
    yield
    assert subject.value() == 42
    raise RuntimeError('async generator exhausted')


def ordinary(fn):
    @wraps(fn)
    def wrapped(*args, **kw):
        return fn(*args, **kw)
    return wrapped


@ordinary
@mark.test.wrapper
def test_params(first, /, second=1, *, third=2):
    raise AssertionError('parameterized tests must not run')
