from .tested.code.lib import subject


# Even an import retry must see the resources discovered by the library's own tests.
assert subject.value() == 42


def test_ok():
    assert not subject.has_web()


def test_consumer_needs_web():
    assert subject.has_web(), 'consumer expected web'
