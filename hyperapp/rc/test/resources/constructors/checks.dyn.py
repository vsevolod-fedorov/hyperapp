import asyncio

from .code.base.mark import mark
from .tested.code import first, second


@mark.test.constructor
def test_first():
    assert first.value() == 'first'
    assert second.value() == 'second'


def test_repeat():
    assert first.value() == 'first'
    assert second.value() == 'second'


async def test_async():
    await asyncio.sleep(0)
    assert second.value() == 'second'


def test_generator():
    yield
    assert first.value() == 'first'


async def test_async_generator():
    yield
    await asyncio.sleep(0)
    assert second.value() == 'second'
