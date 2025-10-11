from . import htypes
from .services import (
    mosaic,
    )
from .tested.code import web_source as web_source_module


def test_web_source_service(web_source):
    ref = mosaic.put("Sample string")
    capsule = web_source(ref)
    assert isinstance(capsule, htypes.builtin.ref)
