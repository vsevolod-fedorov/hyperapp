from .tested.code import left, right


def test_pair():
    assert left.right is right
    assert right.left is left
