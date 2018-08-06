import logging

from ..common.interface import hyper_ref as href_types
from ..common.local_server_paths import LOCAL_ROUTE_RESOLVER_REF_PATH, save_bundle_to_file
from .module import ServerModule

log = logging.getLogger(__name__)


ROUTE_RESOLVER_SERVICE_ID = 'route_resolver'
MODULE_NAME = 'route_resolver_service'


class RouteResolverService(object):

    def __init__(self, route_resolver):
        self._route_resolver = route_resolver

    def rpc_resolve_route(self, request, endpoint_ref):
        transport_ref_set = self._route_resolver.resolve(endpoint_ref)
        return request.make_response_result(transport_ref_list=list(transport_ref_set))


class ThisModule(ServerModule):

    def __init__(self, services):
        super().__init__(MODULE_NAME)
        service = href_types.service(ROUTE_RESOLVER_SERVICE_ID, ['hyper_ref', 'route_resolver'])
        service_ref = services.ref_registry.register_object(href_types.service, service)
        services.service_registry.register(service_ref, RouteResolverService, services.route_resolver)
        ref_collector = services.ref_collector_factory()
        bundle = ref_collector.make_bundle([service_ref])
        ref_path = LOCAL_ROUTE_RESOLVER_REF_PATH
        save_bundle_to_file(bundle, ref_path)
        log.info('Route resolver ref is saved to %s', ref_path)
