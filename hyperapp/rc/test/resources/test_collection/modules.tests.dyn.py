import asyncio

from . import code
from .tested.code import module_1
from .tested.code import module_2
from .tested.code import module_3


def test_fn_1():
    assert module_1.fn_1() == 111


def test_fn_2():
    assert module_2.fn_2() == 222


def test_both_fns():
    assert module_1.fn_1() * 2 == module_2.fn_2()


def test_fn_3():
    assert module_3.fn_3() == 555


async def test_async():
    await asyncio.sleep(0)
    assert module_3.fn_3() == 555


def test_generator():
    yield
    assert module_3.fn_3() == 555


async def test_async_generator():
    yield
    await asyncio.sleep(0)
    assert module_3.fn_3() == 555


# Gets untested module_4 by attribute only when run, so the first run is incomplete,
# and the next one gets it resolved.
def test_code_used_by_run():
    assert code.module_4.fn_4() == 444
