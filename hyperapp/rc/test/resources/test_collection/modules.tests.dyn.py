from .tested.code import module_1
from .tested.code import module_2


def test_fn_1():
    assert module_1.fn_1() == 111


def test_fn_2():
    assert module_2.fn_2() == 222


def test_both_fns():
    assert module_1.fn_1() * 2 == module_2.fn_2()
