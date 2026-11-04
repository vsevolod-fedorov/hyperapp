import asyncio
from functools import wraps

from .code.base.mark import mark
from .tested.code import subject


def ordinary_wrapper(fn):
    @wraps(fn)
    def wrapped(*args, **kw):
        return fn(*args, **kw)
    return wrapped


def test_cached_probe():
    assert subject.value() == 42
    assert subject.value() == 42


def test_bound_probes():
    sample = subject.Sample()
    assert sample.instance() is sample
    assert sample.cls() is subject.Sample
    assert sample.static(42) == 42
    assert subject.Sample.static(42) == 42


@ordinary_wrapper
@mark.test.wrapper
@ordinary_wrapper
@mark.test.wrapper
def test_sync_wrapped():
    assert subject.value() == 42


@mark.test.wrapper
@ordinary_wrapper
@mark.test.wrapper
async def test_async_wrapped():
    await asyncio.sleep(0)
    assert subject.value() == 42


@ordinary_wrapper
@mark.test.wrapper
def test_generator_wrapped():
    yield
    assert subject.value() == 42


@mark.test.wrapper
@ordinary_wrapper
async def test_async_generator_wrapped():
    yield
    await asyncio.sleep(0)
    assert subject.value() == 42
