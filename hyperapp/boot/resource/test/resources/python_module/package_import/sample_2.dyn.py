from . import htypes
from . deep.l1.l2 import l3 as deep_l3
from . override.l1.l2 import l3 as override_l3
from . override import l1 as override_l1


def main():
    assert deep_l3.l4.l5 == 12345
    assert override_l1.l2.l3 == 123
    assert override_l3 == 123
    return htypes.builtin.int(200)
