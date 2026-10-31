from . import htypes
from .tested.code import shapes


def test_line_to():
    line = shapes.line_to(1, 2)
    assert line.end == htypes.sample.point(x=1, y=2)
