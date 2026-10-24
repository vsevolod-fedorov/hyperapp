from . import code
from .tested.code import lazy


def test_fn():
    assert lazy.fn() == 111


# Tests below get untested module_1 only when run, so their first runs are incomplete. Run by the worker
# which ran test_fn before, they get its recorders, which must not report test_fn's use of lazy as theirs.

def test_code_1():
    assert code.module_1.fn_1() == 111


def test_code_2():
    assert code.module_1.fn_1() == 111


def test_code_3():
    assert code.module_1.fn_1() == 111
