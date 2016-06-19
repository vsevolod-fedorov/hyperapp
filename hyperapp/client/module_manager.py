import os.path
import sys
import logging
from types import ModuleType
from ..common.util import is_list_inst
from .registry import DynamicModuleRegistryProxy

log = logging.getLogger(__name__)


DYNAMIC_MODULE_ID_ATTR = 'this_module_id'


class ModuleManager(object):

    def __init__( self, services ):
        self._id2module = {}
        self._services = services
        self._objimpl_registry = services.objimpl_registry
        self._view_registry = services.view_registry

    def add_modules( self, modules ):
        for module in modules:
            self.add_module(module)

    def add_module( self, module ):
        log.info('-- loading module %r package=%r fpath=%r', module.id, module.package, module.fpath)
        self._id2module[module.id] = module
        self._load_module(module)

    def resolve_ids( self, module_ids ):
        modules = []
        for id in module_ids:
            modules.append(self._id2module[id])
        return modules

    def _load_module( self, module, name=None ):
        if name is None:
            name = module.package + '.' + module.id.replace('-', '_')
        name = str(name)  # python expects name and package to be a an str, assume it is
        if name in sys.modules:
            return  # already loaded
        module_inst = ModuleType(name, 'dynamic hyperapp module %r loaded as %r' % (module.id, name))
        sys.modules[name] = module_inst
        ast = compile(module.source, module.fpath, 'exec')  # compile allows to associate file path with loaded module
        module_inst.__dict__[DYNAMIC_MODULE_ID_ATTR] = module.id
        exec(ast, module_inst.__dict__)
        self._register_provided_services(module, module_inst.__dict__)
        return module_inst

    def _register_provided_services( self, module, module_dict ):
        register_objects = module_dict.get('register_objects')
        if register_objects:
            register_objects(DynamicModuleRegistryProxy(self._objimpl_registry, module.id))
        register_views = module_dict.get('register_views')
        if register_views:
            register_views(DynamicModuleRegistryProxy(self._view_registry, module.id), self._services)
