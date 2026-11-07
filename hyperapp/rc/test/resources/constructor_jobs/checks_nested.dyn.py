from .tested.code import subject, other


assert subject.value() == 'ok'
assert subject.value.state['calls'] == 1
assert other.second.state['calls'] == 1


def test_ok():
    assert subject.value() == 'ok'
