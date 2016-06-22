import os.path

# self-registering ifaces:
import hyperapp.common.interface.server_management
import hyperapp.common.interface.admin
import hyperapp.common.interface.fs
import hyperapp.common.interface.blog
import hyperapp.common.interface.article
import hyperapp.common.interface.module_list

from ..common.htypes import iface_registry
from ..common.route_storage import RouteStorage
from .objimpl_registry import ObjImplRegistry
from .view_registry import ViewRegistry
from .transport import TransportRegistry
from .named_url_file_repository import UrlFileRepository
from . import code_repository
from .code_repository import CodeRepository
from .module_manager import ModuleManager
from .file_route_repository import FileRouteRepository
from . import identity
from .identity import FileIdentityRepository, IdentityController
from .cache_repository import CacheRepository
from .proxy_registry import ProxyRegistry
from . import bookmarks
from .bookmarks import Bookmarks
from . import url_clipboard

from . import tcp_transport
from . import encrypted_transport

from . import navigator
from . import splitter
from . import list_view
from . import narrower
from . import text_view
from . import text_edit
from . import form_view

from . import text_object
from . import proxy_object
from . import proxy_list_object


class Services(object):

    def __init__( self ):
        self.iface_registry = iface_registry
        self.route_storage = RouteStorage(FileRouteRepository(os.path.expanduser('~/.local/share/hyperapp/client/routes')))
        self.proxy_registry = ProxyRegistry()
        self.transport_registry = TransportRegistry(self.route_storage, self.proxy_registry)
        self.objimpl_registry = ObjImplRegistry()
        self.view_registry = ViewRegistry(self.transport_registry)
        self.module_mgr = ModuleManager(self)
        self.identity_controller = IdentityController(FileIdentityRepository(os.path.expanduser('~/.local/share/hyperapp/client/identities')))
        self.cache_repository = CacheRepository()
        self.code_repository = CodeRepository(
            self.iface_registry, self.transport_registry, self.cache_repository,
            UrlFileRepository(iface_registry, os.path.expanduser('~/.local/share/hyperapp/client/code_repositories')))
        self.bookmarks = Bookmarks(UrlFileRepository(
            self.iface_registry, os.path.expanduser('~/.local/share/hyperapp/client/bookmarks')))
        self._register_transports()
        self._register_modules()
        self._register_object_implementations()
        self._register_views()

    def _register_transports( self ):
        tcp_transport.register_transports(self.transport_registry, self)
        encrypted_transport.register_transports(self.transport_registry, self)

    def _register_modules( self ):
        for module in [
            identity,
            code_repository,
            bookmarks,
            url_clipboard,
            ]:
            module.ThisModule(self)  # will auto-register itself

    def _register_object_implementations( self ):
        for module in [
                text_object,
                proxy_object,
                proxy_list_object,
                navigator,
                identity,
                bookmarks,
                ]:
            module.register_object_implementations(self.objimpl_registry, self)

    def _register_views( self ):
        for module in [
                navigator,
                splitter,
                list_view,
                narrower,
                text_view,
                text_edit,
                form_view,
                ]:
            module.register_views(self.view_registry, self)
