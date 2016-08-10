import os
import os.path
import logging
from ..common.util import is_list_inst, encode_path
from ..common.htypes import (
    tHierarchyMeta,
    tHierarchyClassMeta,
    tNamed,
    )
from ..common.type_module import tTypeModule, load_types_from_yaml_file

log = logging.getLogger(__name__)


TYPE_MODULE_EXT = '.types.yaml'


class TypeRepository(object):

    class _Rec(object):

        def __init__( self, type_module ):
            assert isinstance(type_module, tTypeModule), repr(type_module)
            self.type_module = type_module

    def __init__( self, dir ):
        self._class2module = {}  # str -> _Rec
        self._load_modules(dir)

    def get_modules_by_requirements( self, requirements ):
        class_paths = set(requirement[1] for requirement in requirements)
        modules = set()
        for requirement in requirements:
            if requirement[0] != 'class': continue
            module = self._class2module.get(requirement[1])
            if module:
                modules.add(module)
        return list(module.type_module for module in modules)

    def _load_modules( self, dir ):
        for fname in os.listdir(dir):
            if fname.endswith(TYPE_MODULE_EXT):
                log.info('loading type module: %r', fname)
                self._load_module(os.path.join(dir, fname))

    def _load_module( self, fpath ):
        type_module = load_types_from_yaml_file(fpath)
        for class_path in self._pick_provided_class_paths(type_module):
            log.info('    provides class %r', class_path)
            self._class2module[class_path] = self._Rec(type_module)

    def _pick_provided_class_paths( self, typedefs ):
        class_paths = []
        for typedef in typedefs:
            t = typedef.type
            if not isinstance(t, tHierarchyClassMeta): continue
            assert isinstance(t.hierarchy, tNamed), repr(name)  # tHierarchyClassMeta.hierarchy must be tNamed
            class_paths.append(encode_path([t.hierarchy.name, t.class_id]))
        return class_paths
