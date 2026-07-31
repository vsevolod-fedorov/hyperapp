from functools import partial

from . import htypes
from .services import (
    pyobj_creg,
    mosaic,
    )
from .code import pick_refs as pick_refs_module
from .code.bundler import Bundler


def make_bundler():
    pick_refs_cache = pick_refs_module.pick_refs_cache()
    pick_refs = partial(pick_refs_module.pick_refs, pick_refs_cache)
    return Bundler(pick_refs)
