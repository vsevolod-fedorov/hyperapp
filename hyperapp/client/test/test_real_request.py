import sys
import os.path
import logging
import asyncio
import unittest
from hyperapp.common.htypes import (
    tModule,
    tClientPacket,
    tRequest,
    IfaceRegistry,
    builtin_type_registry,
    )
from hyperapp.common.url import UrlWithRoutes
from hyperapp.common.visual_rep import pprint
from hyperapp.common.type_repository import TypeRepository
from hyperapp.common.route_storage import RouteRepository, RouteStorage
from hyperapp.common.test.util import PhonyRouteRepository
from hyperapp.client.request import Request, ClientNotification, Response
from hyperapp.client.server import Server
from hyperapp.client.type_registry_registry import TypeRegistryRegistry
from hyperapp.client.module_manager import ModuleManager
from hyperapp.client.remoting import Remoting
from hyperapp.client.objimpl_registry import ObjImplRegistry
from hyperapp.client.named_url_file_repository import NamedUrlRepository
from hyperapp.client.proxy_registry import ProxyRegistry
from hyperapp.client.view_registry import ViewRegistry
from hyperapp.client import tcp_transport
from hyperapp.client import encrypted_transport


TYPE_MODULE_EXT = '.types'
DYN_MODULE_EXT = '.dyn.py'


class PhonyCacheRepository(object):

    def load_value( self, key, t ):
        return []


class PhonyNamedUrlRepository(NamedUrlRepository):

    def enumerate( self ):
        return []

    def add( self, item ):
        pass


class PhonyIdentityRepository(object):

    def add( self, identity_item ):
        pass

    def enumerate( self ):
        return []


class PhonyResourcesManager(object):

    def register_all( self, resources ):
        pass

    def register( self, id, locale, resources ):
        pass

    def resolve( self, id, locale ):
        return None


class Services(object):

    def __init__( self ):
        self.interface_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../common/interface'))
        self.client_module_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        self.iface_registry = IfaceRegistry()
        self.type_registry_registry = TypeRegistryRegistry(dict(builtins=builtin_type_registry()), self.iface_registry)
        self.type_repository = TypeRepository(self.interface_dir, self.iface_registry, self.type_registry_registry)
        self.route_storage = RouteStorage(PhonyRouteRepository())
        self.proxy_registry = ProxyRegistry()
        self.remoting = Remoting(self.route_storage, self.proxy_registry)
        self.objimpl_registry = ObjImplRegistry()
        self.view_registry = ViewRegistry(self.remoting)
        self.module_manager = ModuleManager(self)
        self.identity_repository = PhonyIdentityRepository()
        self.cache_repository = PhonyCacheRepository()
        self.resources_manager = PhonyResourcesManager()
        self.module_manager.register_meta_hook()
        self._load_type_modules()
        self._load_modules()
        self.code_repository.set_url_repository(PhonyNamedUrlRepository())
        self._register_transports()

    def _load_type_modules( self ):
        for module_name in [
                'form',
                'server_management',
                'code_repository',
                ]:
            fpath = os.path.join(self.interface_dir, module_name + TYPE_MODULE_EXT)
            self.type_repository.load_module(module_name, fpath)

    def _load_modules( self ):
        for module_name in [
                'form',
                'code_repository',
                'identity',
                ]:
            fpath = os.path.join(self.client_module_dir, module_name + DYN_MODULE_EXT)
            with open(fpath) as f:
                source = f.read()
            package = 'hyperapp.client'
            module = tModule(id=module_name, package=package, deps=[], satisfies=[], source=source, fpath=fpath)
            self.module_manager.add_code_module(module)

    def _register_transports( self ):
        tcp_transport.register_transports(self.remoting.transport_registry, self)
        encrypted_transport.register_transports(self.remoting.transport_registry, self)


class RealRequestTest(unittest.TestCase):

    def setUp( self ):
        self.services = Services()

    def test_get_request( self ):
        loop = asyncio.get_event_loop()
        loop.set_debug(True)
        loop.run_until_complete(self.run_get_request())

    def test_unsubscribe_notification( self ):
        loop = asyncio.get_event_loop()
        loop.set_debug(True)
        loop.run_until_complete(self.run_unsubscribe_notification())

    @asyncio.coroutine
    def run_get_request( self ):
        url = self.load_url_from_file()
        request = Request(
            iface=url.iface,
            path=url.path,
            command_id='get',
            request_id='test-001',
            params=url.iface.get_request_params_type('get')(),
            )
        pprint(tClientPacket, request.to_data())
        server = Server.from_public_key(self.services.remoting, url.public_key)
        response = yield from (asyncio.wait_for(server.execute_request(request), timeout=0.5))
        self.assertIsInstance(response, Response)
        self.assertEqual('get', response.command_id)
        self.assertEqual('test-001', response.request_id)

    @asyncio.coroutine
    def run_unsubscribe_notification( self ):
        url = self.load_url_from_file()
        notification = ClientNotification(
            iface=url.iface,
            path=url.path,
            command_id='unsubscribe',
            params=url.iface.get_request_params_type('unsubscribe')(),
            )
        pprint(tClientPacket, notification.to_data())
        server = Server.from_public_key(self.services.remoting, url.public_key)
        response = yield from (asyncio.wait_for(server.send_notification(notification), timeout=0.5))
        self.assertEqual(None, response)

    def load_url_from_file( self ):
        url = UrlWithRoutes.load_from_file(self.services.iface_registry, os.path.expanduser('~/tmp/url'))
        self.services.remoting.add_routes_from_url(url)
        return url
