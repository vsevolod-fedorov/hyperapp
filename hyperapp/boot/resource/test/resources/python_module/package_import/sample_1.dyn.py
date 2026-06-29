from . import htypes
from . deep import l1 as deep_l1


def main():
    assert deep_l1.l2.l3.l4.l5 == 12345
    assert override_l1.l2.l3.l4.l5 == 12345
    assert override_l1.l2.l3 == 123
    return htypes.builtin.int(100)
