from .tested.code.lib import subject


def test_ok():
    assert subject.value() == 42
