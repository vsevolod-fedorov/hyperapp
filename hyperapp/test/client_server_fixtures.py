import logging
from collections import namedtuple
from contextlib import contextmanager
import multiprocessing
from multiprocessing.managers import BaseManager
import asyncio

import pytest

from hyperapp.common.visual_rep import pprint
from hyperapp.common.init_logging import init_logging, init_subprocess_logger
from hyperapp.test.utils import log_exceptions, encode_bundle, decode_bundle
from hyperapp.test.test_services import TestServerServices, TestClientServices

log = logging.getLogger(__name__)


common_type_module_list = [
    'error',
    'resource',
    'core',
    'hyper_ref',
    'module',
    'packet',
    ]

common_server_code_module_list = [
    'common.dict_coders',
    'common.visitor',
    'common.route_resolver',
    'common.ref_collector',
    'common.unbundler',
    'common.tcp_packet',
    'server.transport.registry',
    'server.request',
    'server.remoting',
    'server.remoting_proxy',
    ]

common_client_code_module_list = [
    'common.dict_coders',
    'common.visitor',
    'common.route_resolver',
    'common.ref_collector',
    'common.unbundler',
    'common.tcp_packet',
    'client.module_command_registry',
    'client.async_ref_resolver',
    'client.code_registry',
    'client.async_route_resolver',
    'client.endpoint_registry',
    'client.service_registry',
    'client.transport.registry',
    'client.request',
    'client.remoting',
    'client.remoting_proxy',
    ]


Queues = namedtuple('Queues', 'request response')


@pytest.fixture
def queues():
    with multiprocessing.Manager() as manager:
        yield Queues(manager.Queue(), manager.Queue())


class ServerServices(TestServerServices):

    def __init__(self, queues, type_module_list, code_module_list):
        # queues are used by phony transport module
        self.request_queue = queues.request
        self.response_queue = queues.response
        super().__init__(type_module_list, code_module_list)


class Server(object, metaclass=log_exceptions):

    def __init__(self, queues, type_module_list, code_module_list):
        init_subprocess_logger(context='server')
        self.services = ServerServices(queues, type_module_list, code_module_list)
        self.services.start()

    def stop(self):
        self.services.stop()
        assert not self.services.is_failed

    def extract_bundle(self, object_attr):
        ref_collector = self.services.ref_collector_factory()
        ref = getattr(self.services, object_attr)
        bundle = ref_collector.make_bundle([ref])
        pprint(bundle, title='Extracted %r bundle:' % object_attr)
        return encode_bundle(bundle)


class TestManager(BaseManager):
    __test__ = False


TestManager.register('Server', Server)


@pytest.fixture
def test_manager():
    with TestManager() as manager:
        yield manager


@contextmanager
def server_running(test_manager, queues, transport, type_module_list, code_module_list):
    server = test_manager.Server(
        queues,
        common_type_module_list + type_module_list,
        common_server_code_module_list + code_module_list,
        )
    yield server
    log.debug('Test is finished, stopping the server now...')
    server.stop()


class ClientServices(TestClientServices):

    def __init__(self, event_loop, queues, type_module_list, code_module_list):
        # queues are used by phony transport module
        self.request_queue = queues.request
        self.response_queue = queues.response
        super().__init__(event_loop, type_module_list, code_module_list)

    def implant_bundle(self, encoded_bundle):
        bundle = decode_bundle(encoded_bundle)
        self.unbundler.register_bundle(bundle)
        return bundle.roots[0]


@contextmanager
def client_services_running(event_loop, queues, type_module_list, code_module_list):
    event_loop.set_debug(True)
    init_logging('test', context='client')
    services = ClientServices(
        event_loop,
        queues,
        common_type_module_list + type_module_list,
        common_client_code_module_list + code_module_list,
        )
    services.start()
    yield services
    services.stop()


@pytest.fixture(params=['phony', 'tcp'])
def transport(request):
    return request.param

def transport_type_module_list(transport):
    return ['%s_transport' % transport]

def transport_server_code_module_list(transport):
    return ['server.transport.%s' % transport]

def transport_client_code_module_list(transport):
    return ['client.transport.%s' % transport]
