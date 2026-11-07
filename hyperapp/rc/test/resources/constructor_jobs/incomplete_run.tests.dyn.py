from .code import missing
from .tested.code import subject


def test_incomplete():
    subject.value()
    missing.fn()
