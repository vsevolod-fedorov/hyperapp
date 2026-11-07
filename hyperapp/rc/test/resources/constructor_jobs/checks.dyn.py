import asyncio

from .tested.code import subject


def test_ok():
    assert subject.value() == 'ok'


def test_fail():
    subject.value('failed observation')
    raise RuntimeError('failed test')


async def test_async_failure():
    subject.value('not published')
    await asyncio.sleep(0)
    raise RuntimeError('late failure')


def test_generator_failure():
    subject.value('not published')
    yield
    raise RuntimeError('late failure')


async def test_async_generator_failure():
    subject.value('not published')
    yield
    raise RuntimeError('late failure')
