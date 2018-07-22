import logging

from ..common.interface import hyper_ref as href_types
from ..common.ref import decode_capsule
from ..common.route_resolver import RouteSource
from .registry import UnknownRegistryIdError, Registry
from .request import Request, Response
from .module import ServerModule

log = logging.getLogger(__name__)


MODULE_NAME = 'remoting'


class ServiceRegistry(Registry):

    def resolve(self, service_ref):
        rec = self._resolve(service_ref)
        log.info('producing service for %r using %s(%s, %s)', service_ref, rec.factory, rec.args, rec.kw)
        return rec.factory(*rec.args, **rec.kw)


class LocalTransport(object):

    def __init__(self, address, types, ref_registry, ref_resolver, route_resolver, transport_resolver, service_registry):
        self._types = types
        self._ref_registry = ref_registry
        self._ref_resolver = ref_resolver
        self._route_resolver = route_resolver
        self._transport_resolver = transport_resolver
        self._service_registry = service_registry

    def send(self, ref):
        capsule = self._ref_resolver.resolve_ref(ref)
        assert capsule.full_type_name == ['hyper_ref', 'rpc_message'], capsule.full_type_name
        rpc_request = decode_capsule(self._types, capsule)
        assert isinstance(rpc_request, href_types.rpc_request), repr(rpc_request)
        rpc_response = self._process_request(rpc_request)
        self._send_rpc_response(rpc_response)

    def _send_rpc_response(self, rpc_response):
        rpc_response_ref = self._ref_registry.register_object(href_types.rpc_message, rpc_response)
        transport_ref_set = self._route_resolver.resolve(rpc_response.target_endpoint_ref)
        assert len(transport_ref_set) == 1  # todo: multiple transport support
        transport = self._transport_resolver.resolve(transport_ref_set.pop())
        transport.send(rpc_response_ref)

    def _process_request(self, rpc_request):
        iface = self._types.resolve(rpc_request.iface_full_type_name)
        command = iface[rpc_request.command_id]
        params = rpc_request.params.decode(command.request)
        servant = self._service_registry.resolve(rpc_request.target_service_ref)
        request = Request(rpc_request.source_endpoint_ref, command)
        method = getattr(servant, 'rpc_' + rpc_request.command_id, None)
        assert method, '%r does not implement method remote_%s' % (servant, rpc_request.command_id)
        response = method(request, **params._asdict())
        if not command.is_request:
            assert not response, 'No results are expected from notifications'
            return
        assert response, 'Use request.make_response method to return results from requests'
        assert isinstance(response, Response)
        rpc_response = response.make_rpc_response(command, rpc_request.request_id)
        return rpc_response


class LocalRouteSource(RouteSource):

    def __init__(self, service_registry, local_transport_ref_set):
        self._service_registry = service_registry
        self._local_transport_ref_set = local_transport_ref_set

    def resolve(self, service_ref):
        if self._service_registry.is_registered(service_ref):
            return self._local_transport_ref_set
        else:
            return set()


class Remoting(object):

    def __init__(self, types, ref_registry, ref_resolver, route_resolver, transport_resolver):
        self._types = types
        self._ref_registry = ref_registry
        self._ref_resolver = ref_resolver
        self._route_resolver = route_resolver
        self._transport_resolver = transport_resolver

    def process_rpc_request(self, rpc_request_ref, rpc_request):
        transport_ref_set = self._route_resolver.resolve(rpc_request.target_service_ref)
        assert len(transport_ref_set) == 1, repr(transport_ref_set)  # todo: multiple transport support
        transport = self._transport_resolver.resolve(transport_ref_set.pop())
        transport.send(rpc_request_ref)


class ThisModule(ServerModule):

    def __init__(self, services):
        super().__init__(MODULE_NAME)
        self._ref_registry = services.ref_registry
        services.service_registry = service_registry = ServiceRegistry()
        services.remoting = Remoting(
            services.types,
            services.ref_registry,
            services.ref_resolver,
            services.route_resolver,
            services.transport_resolver,
            )
        services.transport_registry.register(
            href_types.local_transport_address,
            LocalTransport,
            services.types,
            services.ref_registry,
            services.ref_resolver,
            services.route_resolver,
            services.transport_resolver,
            services.service_registry,
            )
        local_route_source = LocalRouteSource(service_registry, services.local_transport_ref_set)
        services.route_resolver.add_source(local_route_source)
