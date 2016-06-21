import os.path

# self-registering ifaces:
import hyperapp.common.interface.server_management
import hyperapp.common.interface.admin
import hyperapp.common.interface.fs
import hyperapp.common.interface.blog
import hyperapp.common.interface.article
import hyperapp.common.interface.module_list
# self-registering views:
import hyperapp.client.text_object
import hyperapp.client.proxy_list_object
import hyperapp.client.identity
import hyperapp.client.code_repository
import hyperapp.client.bookmarks
import hyperapp.client.url_clipboard

from ..common.htypes import iface_registry
from .objimpl_registry import objimpl_registry
from .view_registry import view_registry
from .code_repository import CodeRepository, UrlFileRepository
from .module_manager import ModuleManager
from .route_repository import FileRouteRepository, RouteStorage
from .identity import get_identity_controller
from .cache_repository import cache_repository
from .proxy_registry import proxy_registry

from hyperapp.client.transport import transport_registry
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
        self.route_repo = RouteStorage(FileRouteRepository(os.path.expanduser('~/.local/share/hyperapp/client/routes')))
        self.iface_registry = iface_registry
        self.objimpl_registry = objimpl_registry
        self.view_registry = view_registry
        self.module_mgr = ModuleManager(self)
        self.identity_controller = get_identity_controller()
        self.transport_registry = transport_registry
        self.cache_repository = cache_repository
        self.code_repository = CodeRepository(
            self.iface_registry, self.cache_repository,
            UrlFileRepository(iface_registry, os.path.expanduser('~/.local/share/hyperapp/client/code_repositories')))
        self.proxy_registry = proxy_registry
        self._register_transports()
        self._register_views()
        self._register_object_implementations()

    def _register_transports( self ):
        tcp_transport.register_transports(self.transport_registry, self)
        encrypted_transport.register_transports(self.transport_registry, self)

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

    def _register_object_implementations( self ):
        for module in [
                text_object,
                proxy_object,
                proxy_list_object,
                ]:
            module.register_object_implementations(self.objimpl_registry, self)
