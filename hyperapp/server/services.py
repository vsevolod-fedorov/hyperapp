import os.path
from ..common.htypes import iface_registry
from ..common.route_storage import RouteStorage
from .module import Module
from . import route_storage
from .remoting import Remoting
from . import tcp_transport
from . import encrypted_transport
from . import code_repository
from .code_repository import ModuleRepository, CodeRepository
from .type_repository import TypeRepository
from .resources_loader import ResourcesLoader


class Services(object):

    def __init__( self ):
        self.iface_registry = iface_registry
        server_dir = os.path.abspath(os.path.dirname(__file__))
        interface_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../common/interface'))
        dynamic_modules_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../dynamic_modules'))
        self.resources_loader = ResourcesLoader(dict(interface=server_dir,
                                                     client_module=dynamic_modules_dir))
        self.route_storage_module = route_storage.ThisModule()
        self.module_repository = ModuleRepository(dynamic_modules_dir)
        self.code_repository = CodeRepository(self.module_repository, self.resources_loader)
        self.type_repository = TypeRepository(interface_dir)
        self._register_modules()
        Module.init_phases()
        self.route_storage = RouteStorage(route_storage.DbRouteRepository(self.route_storage_module))
        self.remoting = Remoting(self.iface_registry)
        self._register_transports()

    def _register_modules( self ):
        for module in [code_repository]:
            instance = module.ThisModule(self)  # will auto-register itself
            module.this_module = instance
        
    def _register_transports( self ):
        for module in [tcp_transport, encrypted_transport]:
            module.register_transports(self.remoting.transport_registry, self)
