import queue
import logging

import pytest

from hyperapp.common.htypes.packet_coders import packet_coders
from hyperapp.common import cdr_coders  # self-registering

log = logging.getLogger(__name__)


pytest_plugins = ['hyperapp.common.test.services']


@pytest.fixture
def type_module_list():
    return [
        'rsa_identity',
        'rpc',
        'test_rpc',
        'echo',
        ]


@pytest.fixture
def code_module_list():
    return [
        'common.visitor',
        'common.ref_collector',
        'common.unbundler',
        'common.remoting.identity',
        'common.remoting.rsa_identity',
        'sync.work_dir',
        'sync.async_stop',
        'sync.transport.transport',
        'sync.transport.endpoint',
        'sync.rpc.rpc_proxy',
        'sync.rpc.rpc_endpoint',
        'sync.subprocess_connection',
        'sync.subprocess',
        ]


class Servant:

    def __init__(self, echo_response_queue, types, rpc_proxy, rpc_endpoint):
        self._echo_response_queue = echo_response_queue
        self._types = types
        self._rpc_proxy = rpc_proxy
        self._rpc_endpoint = rpc_endpoint

    def run(self, request, echo_service_ref):
        echo_service = self._types.resolve_ref(echo_service_ref).value
        echo = self._rpc_proxy(request.receiver_identity, self._rpc_endpoint, echo_service)
        response = echo.echo('Hello')
        self._echo_response_queue.put(response)


def test_echo(services, htypes):
    master_identity = services.generate_rsa_identity(fast=True)
    master_peer_ref = services.mosaic.put(master_identity.peer.piece)

    object_id = 'run_test'
    test_echo_iface_ref = services.types.reverse_resolve(htypes.test_rpc.test_echo_iface)
    master_service = htypes.rpc.endpoint(
        peer_ref=master_peer_ref,
        iface_ref=test_echo_iface_ref,
        object_id=object_id,
        )
    master_service_ref = services.mosaic.put(master_service)

    rpc_endpoint = services.rpc_endpoint()
    services.endpoint_registry.register(master_identity, rpc_endpoint)

    echo_response_queue = queue.Queue()
    servant = Servant(echo_response_queue, services.types, services.rpc_proxy, rpc_endpoint)
    rpc_endpoint.register_servant(object_id, servant)

    ref_collector = services.ref_collector_factory()
    master_service_bundle = ref_collector.make_bundle([master_service_ref])
    master_service_bundle_cdr = packet_coders.encode('cdr', master_service_bundle)

    master_peer_ref_cdr_list = [packet_coders.encode('cdr', master_peer_ref)]

    subprocess = services.subprocess(
        'subprocess',
        type_module_list=[
            'rsa_identity',
            'rpc',
            'test_rpc',
            'echo',
            ],
        code_module_list=[
            'common.visitor',
            'common.ref_collector',
            'common.unbundler',
            'common.remoting.identity',
            'common.remoting.rsa_identity',
            'sync.async_stop',
            'sync.transport.transport',
            'sync.transport.endpoint',
            'sync.subprocess_connection',
            'sync.subprocess_child',
            'sync.rpc.rpc_proxy',
            'sync.rpc.rpc_endpoint',
            'sync.rpc.test.echo_service',
            ],
        config = {
            'sync.rpc.test.echo_service': {'master_service_bundle_cdr': master_service_bundle_cdr},
            'sync.subprocess_child': {'master_peer_ref_cdr_list': master_peer_ref_cdr_list},
            },
        )
    with subprocess:
        log.info("Waiting for echo response.")
        response = echo_response_queue.get(timeout=10)
        log.info("Got echo response: %s.", response)
        assert response.response == 'Hello to you too'
    log.info("Subprocess is finished.")
