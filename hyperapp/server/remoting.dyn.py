from datetime import datetime
import logging
from operator import attrgetter
import uuid

from dateutil.tz import tzlocal

from hyperapp.common.htypes import EncodableEmbedded
from hyperapp.common.ref import ref_repr, ref_list_repr
from hyperapp.common.visual_rep import pprint
from hyperapp.common.registry import UnknownRegistryIdError, Registry
from hyperapp.common.module import Module
from .request import Request, Response
from .route_resolver import RouteSource
from .htypes.hyper_ref import route_rec

log = logging.getLogger(__name__)


class ServiceRegistry(Registry):

    def id_to_str(self, id):
        return ref_repr(id)

    def resolve(self, service_ref):
        rec = self._resolve(service_ref)
        log.info('ServiceRegistry: producing service for %s using %s(%s, %s)', ref_repr(service_ref), rec.factory, rec.args, rec.kw)
        return rec.factory(*rec.args, **rec.kw)


class LocalRouteSource(RouteSource):

    def __init__(self, service_registry, local_transport_ref_set):
        self._service_registry = service_registry
        self._local_transport_ref_set = local_transport_ref_set

    def resolve(self, service_ref):
        if self._service_registry.is_registered(service_ref):
            now = datetime.now(tzlocal())
            return {route_rec(transport_ref, now) for transport_ref in self._local_transport_ref_set}
        else:
            return set()


class Remoting(object):

    def __init__(self, ref_resolver, types, mosaic, route_resolver, transport_registry, service_registry):
        self._ref_resolver = ref_resolver
        self._types = types
        self._mosaic = mosaic
        self._route_resolver = route_resolver
        self._transport_registry = transport_registry
        self._service_registry = service_registry
        my_endpoint = htypes.hyper_ref.endpoint(service_id=str(uuid.uuid4()))
        self._my_endpoint_ref = self._mosaic.put(my_endpoint)
        # todo: may be create server endpoint registry and register my endpoint there

    def send_request(self, service_ref, iface, command, params):
        route_rec_set = self._route_resolver.resolve(service_ref)
        assert route_rec_set, 'No routes for service %s' % ref_repr(service_ref)
        route_rec = sorted(route_rec_set, key=attrgetter('available_at'))[-1]  # pick freshest route
        transport = self._transport_registry.invite(route_rec.transport_ref)
        if command.is_request:
            request_id = str(uuid.uuid4())
        else:
            request_id = None
        iface_type_ref = self._types.reverse_resolve(iface)
        rpc_request = htypes.hyper_ref.rpc_request(
            iface_type_ref=iface_type_ref,
            source_endpoint_ref=self._my_endpoint_ref,
            target_service_ref=service_ref,
            command_id=command.command_id,
            request_id=request_id,
            params=EncodableEmbedded(command.request, params),
            )
        request_ref = self._mosaic.put(rpc_request)
        pprint(rpc_request, title='Outgoing RPC %s %s:' % (command.request_type, ref_repr(request_ref)))
        pprint(params, title='params:')
        transport.send(request_ref)
        assert not command.is_request, 'Only sending notifications is now supported for server'

    def process_rpc_request(self, rpc_request_ref, rpc_request):
        capsule = self._ref_resolver.resolve_ref(rpc_request_ref)
        rpc_request = self._types.decode_capsule(capsule, expected_type=htypes.hyper_ref.rpc_message).value
        assert isinstance(rpc_request, htypes.hyper_ref.rpc_request), repr(rpc_request)
        rpc_response_ref, rpc_response = self._process_request(rpc_request_ref, rpc_request)
        if rpc_response is not None:
            self._send_rpc_response(rpc_response_ref, rpc_response)

    def _send_rpc_response(self, rpc_response_ref, rpc_response):
        route_rec_set = self._route_resolver.resolve(rpc_response.target_endpoint_ref)
        assert route_rec_set, 'No routes for service %s' % ref_repr(rpc_response.target_endpoint_ref)
        route_rec = sorted(route_rec_set, key=attrgetter('available_at'))[-1]  # pick freshest route
        transport = self._transport_registry.invite(route_rec.transport_ref)
        transport.send(rpc_response_ref)

    def _process_request(self, rpc_request_ref, rpc_request):
        iface = self._types.resolve(rpc_request.iface_type_ref)
        command = iface[rpc_request.command_id]
        pprint(rpc_request, title='Incoming RPC %s %s:' % (command.request_type, ref_repr(rpc_request_ref)))
        params = rpc_request.params.decode(command.request)
        pprint(params, title='params:')
        servant = self._service_registry.resolve(rpc_request.target_service_ref)
        request = Request(rpc_request.source_endpoint_ref, command)
        method_name = 'rpc_' + rpc_request.command_id
        method = getattr(servant, method_name, None)
        log.info('Calling %s %r', command.request_type, method)
        assert method, '%r does not implement method %s' % (servant, method_name)
        response = self._call_servant(command, method, request, params)
        if response is None:
            return (None, None)
        assert isinstance(response, Response), repr(response)
        rpc_response = response.make_rpc_response(command, rpc_request.request_id)
        rpc_response_ref = self._mosaic.put(rpc_response)
        pprint(rpc_response, title='Outgoing RPC Response %s:' % ref_repr(rpc_response_ref))
        response.log_result_or_error(command)
        return (rpc_response_ref, rpc_response)

    def _call_servant(self, command, method, request, params):
        try:
            response = method(request, **params._asdict())
        except Exception as x:
            assert command.is_request  # todo: error handling for notifications
            if isinstance(x, htypes.error.error):
                error = x
            else:
                log.exception('Error processing %s %r:', command.request_type, method)
                error = htypes.error.server_error()
            return request.make_response(error=error)
        if not command.is_request:
            assert not response, 'No results are expected from notifications'
            return None
        if command.response.fields:
            assert response, 'Use request.make_response method to return results from requests'
        else:
            # No fields in response, servant is allowed to return None
            if not response:
                response = request.make_response_result()
        return response


class ThisModule(Module):

    def __init__(self, module_name, services, config):
        super().__init__(module_name)
        self._mosaic = services.mosaic
        services.service_registry = service_registry = ServiceRegistry()
        services.remoting = Remoting(
            services.ref_resolver,
            services.types,
            services.mosaic,
            services.route_resolver,
            services.transport_registry,
            services.service_registry,
            )
        local_route_source = LocalRouteSource(service_registry, services.local_transport_ref_set)
        services.route_resolver.add_source(local_route_source)
