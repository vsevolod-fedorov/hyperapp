import logging
import uuid
import asyncio
from collections import namedtuple

from ..common.interface import hyper_ref as href_types
from ..common.htypes import EncodableEmbedded
from ..common.visual_rep import pprint
from .module import ClientModule

log = logging.getLogger(__name__)


MODULE_NAME = 'remoting'


PendingRequest = namedtuple('PendingRequest', 'iface command future')


class Remoting(object):

    def __init__(self, ref_registry, async_route_resolver, endpoint_registry, transport_resolver):
        self._ref_registry = ref_registry
        self._async_route_resolver = async_route_resolver
        self._transport_resolver = transport_resolver
        self._pending_requests = {}  # request id -> PendingRequest
        self._my_endpoint_ref = endpoint_registry.register_endpoint(href_types.endpoint(
            service_id=str(uuid.uuid4())))

    async def send_request(self, service_ref, iface, command, params):
        transport_ref_set = await self._async_route_resolver.resolve(service_ref)
        assert len(transport_ref_set) == 1, repr(transport_ref_set)  # todo: multiple transport support
        transport = await self._transport_resolver.resolve(transport_ref_set.pop())
        if command.is_request:
            request_id = str(uuid.uuid4())
        else:
            request_id = None
        rpc_request = href_types.rpc_request(
            iface_full_type_name=iface.full_name,
            source_endpoint_ref=self._my_endpoint_ref,
            target_service_ref=service_ref,
            command_id=command.command_id,
            request_id=request_id,
            params=EncodableEmbedded(command.request, params),
            )
        log.info('RPC request:')
        pprint(href_types.rpc_request, rpc_request)
        log.info('params:')
        pprint(command.request, params)
        request_ref = self._ref_registry.register_object(href_types.rpc_message, rpc_request)
        transport.send(request_ref)
        if not command.is_request:
            return
        future = asyncio.Future()
        self._pending_requests[request_id] = PendingRequest(iface, command, future)
        try:
            log.info('Remoting: awaiting for response future...')
            result = (await future)
            log.info('Remoting: got result future: %r', result)
            return result
        finally:
            del self._pending_requests[request_id]

    def process_rpc_response(self, rpc_response_ref, rpc_response):
        log.info('Remoting: processing RPC Response: %r', rpc_response)
        pprint(href_types.rpc_response, rpc_response)
        assert rpc_response.is_succeeded  # todo
        request = self._pending_requests.get(rpc_response.request_id)
        if not request:
            log.warning('No one is waiting for response %r; ignoring', rpc_response.request_id)
            return
        result_t = request.iface[request.command.command_id].response
        result = rpc_response.result_or_error.decode(result_t)
        log.info('Result:')
        pprint(result_t, result)
        request.future.set_result(result)
        log.info('Remoting: processing response: done')
        return True  # todo: do not use registry to process packets


class ThisModule(ClientModule):

    def __init__(self, services):
        super().__init__(MODULE_NAME, services)
        services.remoting = remoting = Remoting(
            services.ref_registry,
            services.async_route_resolver,
            services.endpoint_registry,
            services.transport_resolver,
            )
