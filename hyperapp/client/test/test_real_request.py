import sys
import os.path
import logging
import asyncio
import unittest
from hyperapp.common.htypes import (
    tClientPacket,
    tRequest,
    IfaceRegistry,
    )
from hyperapp.common.endpoint import Url
from hyperapp.common.visual_rep import pprint
from hyperapp.client.request import Request, ClientNotification, Response
from hyperapp.client.server import Server
from hyperapp.client import code_repository
from hyperapp.client.module_manager import ModuleManager
from hyperapp.client.transport import transport_registry
from hyperapp.client.objimpl_registry import objimpl_registry
from hyperapp.client.view_registry import view_registry
from hyperapp.common.interface.server_management import server_management_iface

from hyperapp.client import tcp_transport
from hyperapp.client import encrypted_transport


class RealRequestTest(unittest.TestCase):

    def setUp( self ):
        self.iface_registry = IfaceRegistry()
        self.module_mgr = ModuleManager()
        self.code_repository = code_repository.get_code_repository()
        tcp_transport.register_transports(transport_registry, self.module_mgr, self.code_repository,
                                          self.iface_registry, objimpl_registry, view_registry)
        self.iface_registry.register(server_management_iface)

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
        url = Url.from_str(self.iface_registry, open(os.path.expanduser('~/tmp/url')).read())
        request = Request(
            iface=url.iface,
            path=url.path,
            command_id='get',
            request_id='test-001',
            params=url.iface.get_request_params_type('get')(),
            )
        pprint(tClientPacket, request.to_data())
        server = Server.from_endpoint(url.endpoint)
        response = yield from (asyncio.wait_for(server.execute_request(request), timeout=0.5))
        self.assertIsInstance(response, Response)
        self.assertEqual('get', response.command_id)
        self.assertEqual('test-001', response.request_id)

    @asyncio.coroutine
    def run_unsubscribe_notification( self ):
        url = Url.from_str(self.iface_registry, open(os.path.expanduser('~/tmp/url')).read())
        notification = ClientNotification(
            iface=url.iface,
            path=url.path,
            command_id='unsubscribe',
            params=url.iface.get_request_params_type('unsubscribe')(),
            )
        pprint(tClientPacket, notification.to_data())
        server = Server.from_endpoint(url.endpoint)
        response = yield from (asyncio.wait_for(server.send_notification(notification), timeout=0.5))
        self.assertEqual(None, response)
