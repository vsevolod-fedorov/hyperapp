import asyncio

from .tested import code
from .tested.code import module_1


# Tests below get module_2 by attribute only when they run, after an await or yield. Tested modules are
# decided by the test module import, so they fail right away. Failing, they show tests are run to their end.

async def test_async():
    await asyncio.sleep(0)
    assert code.module_2.fn_2() == 222


def test_generator():
    yield
    assert code.module_2.fn_2() == 222


async def test_async_generator():
    yield
    await asyncio.sleep(0)
    assert code.module_2.fn_2() == 222
