from .tested.code import subject


def test_ok():
    assert subject.value() == 42
