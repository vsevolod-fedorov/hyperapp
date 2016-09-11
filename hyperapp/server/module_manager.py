import logging
from ..common import module_manager as common_module_manager

log = logging.getLogger(__name__)


class ModuleManager(common_module_manager.ModuleManager):

    def __init__( self, services, type_module_registry ):
        common_module_manager.ModuleManager.__init__(self, services, type_module_registry)

    def add_code_module( self, module ):
        log.info('loading code module %r package=%r fpath=%r', module.id, module.package, module.fpath)
        self._load_module(module)