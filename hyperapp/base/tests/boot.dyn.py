from functools import partial

from . import htypes
from .services import (
    mosaic,
    )
from .code import pick_refs as pick_refs_module
from .code.bundler import Bundler


def boot(args):
    print(f"Hello from boot; args={args!r}")
    pick_refs_cache = pick_refs_module.pick_refs_cache()
    pick_refs = partial(pick_refs_module.pick_refs, pick_refs_cache)
    bundler = Bundler(pick_refs)
    rec = htypes.test.empty_record()
    print("rec:", rec)
    return args[0] + 100
