# A plain importable name lets the other modules try importing this test as code.
from .tested.code import subject


def test_ok():
    assert subject.value() == 42
