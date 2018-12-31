from pathlib import Path
import sys
from types import SimpleNamespace
import logging
import abc

from .htypes import register_builtin_types
from .local_type_module import LocalTypeModuleRegistry
from .code_module import code_module_t
from .ref_registry import RefRegistry
from .ref_resolver import RefResolver
from .type_module_loader import TypeModuleLoader
from .type_resolver import TypeResolver
from .code_module import LocalCodeModuleRegistry, register_code_module_types
from .code_module_loader import CodeModuleLoader
from .code_module_importer import CodeModuleImporter
from .module import ModuleRegistry


log = logging.getLogger(__name__)


TYPE_MODULE_EXT = '.types'
HYPERAPP_DIR = Path(__file__).parent.joinpath('../..').resolve()


class ServicesBase(object, metaclass=abc.ABCMeta):

    def __init__(self):
        self.hyperapp_dir = HYPERAPP_DIR / 'hyperapp'
        self.interface_dir = self.hyperapp_dir / 'common' / 'interface'
        self.on_start = []
        self.on_stop = []
        self.config = {}
        self.failure_reason_list = []
        self._is_stopped = False

    def init_services(self, config=None):
        self.config.update(config or {})
        self.ref_resolver = RefResolver()
        self.type_resolver = TypeResolver(self.ref_resolver)
        self.ref_registry = RefRegistry(self.type_resolver)
        register_builtin_types(self.ref_registry, self.type_resolver)
        register_code_module_types(self.ref_registry, self.type_resolver)
        self.ref_resolver.add_source(self.ref_registry)
        self.local_type_module_registry = LocalTypeModuleRegistry()
        self.local_code_module_registry = LocalCodeModuleRegistry()
        self.type_module_loader = TypeModuleLoader(self.type_resolver, self.ref_registry, self.local_type_module_registry)
        self.code_module_loader = CodeModuleLoader(self.ref_registry, self.local_type_module_registry, self.local_code_module_registry)
        self.module_registry = ModuleRegistry()
        self.code_module_importer = CodeModuleImporter(self.type_resolver)
        self.code_module_importer.register_meta_hook()

    def start(self):
        for start in self.on_start:
            start()

    def stop(self):
        if self._is_stopped:
            log.info('Already stopped.')
            return
        log.info('Stopping modules...')
        for stop in self.on_stop:
            stop()
        log.info('Stopping modules: done')
        self.on_stopped()
        self._is_stopped = True

    def failed(self, reason):
        log.error('Failed: %r', reason)
        self.failure_reason_list.append(reason)
        self.schedule_stopping()

    @abc.abstractmethod
    def schedule_stopping(self):
        pass

    @property
    def is_failed(self):
        return self.failure_reason_list != []

    def on_stopped(self):
        pass
        
    def _load_type_module_list(self, module_name_list):
        for module_name in module_name_list:
            file_path = self.interface_dir.joinpath(module_name).with_suffix(TYPE_MODULE_EXT)
            self.type_module_loader.load_type_module(file_path, module_name)

    def _load_code_module_list(self, module_name_list):
        for module_name in module_name_list:
            parts = module_name.split('.')
            file_path = self.interface_dir.joinpath(*parts)
            self.code_module_loader.load_code_module(file_path, module_name)
