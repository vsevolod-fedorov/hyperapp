from . import htypes
from .services import (
    mosaic,
    web,
    )

# Calls a service at import time; boot services are given to imports up front, so import is complete.
origin_ref = mosaic.put(htypes.sample.point(x=0, y=0))


# Uses web only when called, so only a test run finds it is used.
def load(ref):
    return web.summon(ref)
