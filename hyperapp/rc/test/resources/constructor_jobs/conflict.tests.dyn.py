from .tested.code import subject


def test_first():
    assert subject.value('first') == 'first'


def test_repeat():
    assert subject.value('first') == 'first'


def test_conflict():
    assert subject.value('contradiction') == 'contradiction'
