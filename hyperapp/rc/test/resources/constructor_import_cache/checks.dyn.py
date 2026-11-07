from .tested.code import subject, other


# The retry must execute the probes now, even before a test job has run on this worker.
assert subject.import_only() == 'ok'
assert subject.import_only.state['calls'] == 1
assert other.value.state['calls'] == 1


def test_0():
    assert subject.f0() == 'ok'


def test_1():
    assert subject.f1() == 'ok'


def test_2():
    assert subject.f2() == 'ok'


def test_3():
    assert subject.f3() == 'ok'
