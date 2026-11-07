from .tested.code import provider, dependency
from . import code


assert provider.import_only()
assert dependency.import_only.state['calls'] == 1
# The first retry calls the nested provider, then needs another dependency resolved.
assert code.extra.value() == 42


def test_ok():
    assert provider.value() == 42
    assert dependency.value.state['calls'] == 1
