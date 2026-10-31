from . import htypes
from .services import mosaic
from .tested.code import codec


def test_load():
    point = htypes.sample.point(x=1, y=2)
    assert codec.load(mosaic.put(point)) == point
    assert codec.origin_ref == mosaic.put(htypes.sample.point(x=0, y=0))
