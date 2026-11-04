from . import code
from .tested.code import subject


def test_a_incomplete():
    assert code.late.get_value() == 42


def test_b_failure():
    assert subject.fn.test_marker == 'function'
    raise RuntimeError('expected test failure')


def test_c_success():
    assert subject.fn.test_marker == 'function'
    assert subject.fn() == 'subject'
