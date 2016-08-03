import asyncio
from PySide import QtCore, QtGui
from ..common.htypes import iface_registry
from ..common.url import UrlWithRoutes
from .command import command
from .module import Module
from .proxy_object import execute_get_request


class ThisModule(Module):

    def __init__( self, services ):
        Module.__init__(self, services)
        self._remoting = services.remoting

    def get_object_commands( self, object ):
        if object.get_url() is not None:
            return [self.command_url_to_clipboard]
        return []

    @command('url_from_clipboard')
    @asyncio.coroutine
    def command_url_from_clipboard( self ):
        url_str = QtGui.QApplication.clipboard().text()
        url = UrlWithRoutes.from_str(iface_registry, url_str)
        self._remoting.add_routes(url.public_key, url.routes)
        return execute_get_request(self._remoting, url)

    @command('url_to_clipboard', kind='object')
    def command_url_to_clipboard( self, object ):
        url = object.get_url()
        assert url is not None
        enriched_url = self._remoting.add_routes_to_url(url)
        QtGui.QApplication.clipboard().setText(enriched_url.to_str())
