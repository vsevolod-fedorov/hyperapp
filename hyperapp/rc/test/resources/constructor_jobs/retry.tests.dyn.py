from .tested.code import subject


assert subject.value() == 'ok'
assert subject.value.state['calls'] == 1


def test_ok():
    assert subject.value() == 'ok'
