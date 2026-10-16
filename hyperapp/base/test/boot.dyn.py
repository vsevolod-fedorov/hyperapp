from functools import partial

from hyperapp.boot.code_registry import CodeRegistry

from . import htypes
from .services import (
    pyobj_creg,
    mosaic,
    unbundler,
    web,
    )
from .code import pick_refs as pick_refs_module
from .code.bundler import Bundler
from .code import resource_name
from .code import builtin_name
from .code import resource_dump


def make_bundler(assoc_pickers):
    pick_refs_cache = pick_refs_module.pick_refs_cache()
    pick_refs = partial(pick_refs_module.pick_refs, pick_refs_cache)
    def bundler(ref, seen_refs=None, size_limit=None):
        return Bundler(assoc_pickers, pick_refs).run(ref, seen_refs, size_limit)
    return bundler


def make_name_resources():
    pick_refs_cache = pick_refs_module.pick_refs_cache()
    pick_refs = partial(pick_refs_module.pick_refs, pick_refs_cache)
    # This boot has no system services, so build the registry from the same actors as base config does.
    resource_name_creg = CodeRegistry(pyobj_creg, web, 'resource_name_creg', {
        htypes.builtin.python_module: builtin_name.python_module_resource_name,
        htypes.builtin.attribute: builtin_name.attribute_resource_name,
        })
    return partial(resource_name.name_resources, resource_name_creg, pick_refs)
