from .tested.code import subject


def test_value():
    assert subject.value() == 42
