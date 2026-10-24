# Test runs get manual modules imported by tested ones.
from .tested.code import user


def test_fn():
    assert user.fn() == 1
