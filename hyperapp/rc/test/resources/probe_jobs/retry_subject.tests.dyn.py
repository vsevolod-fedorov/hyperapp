from .tested.code import subject


assert subject.value() == 42
assert subject.value.state['calls'] == 1


def test_ok():
    assert subject.value() == 42
    # Re-importing this module would call value twice in this job.
    assert subject.value.state['calls'] == 1
