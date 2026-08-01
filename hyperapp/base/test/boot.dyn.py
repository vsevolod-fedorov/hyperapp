from functools import partial

from . import htypes
from .services import (
    pyobj_creg,
    mosaic,
    unbundler,
    )
from .code import pick_refs as pick_refs_module
from .code.bundler import Bundler


def make_bundler():
    pick_refs_cache = pick_refs_module.pick_refs_cache()
    pick_refs = partial(pick_refs_module.pick_refs, pick_refs_cache)
    def bundler(ref, seen_refs=None, size_limit=None):
        return Bundler(pick_refs).run(ref, seen_refs, size_limit)
    return bundler
