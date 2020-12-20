import logging

from hyperapp.common.module import Module
from . import htypes
from .local_server_paths import LOCAL_ROUTE_RESOLVER_REF_PATH, save_bundle_to_file

log = logging.getLogger(__name__)


ROUTE_RESOLVER_SERVICE_ID = 'route_resolver'


class RouteResolverService(object):

    def __init__(self, route_resolver):
        self._route_resolver = route_resolver

    def rpc_resolve_route(self, request, endpoint_ref):
        route_rec_set = self._route_resolver.resolve(endpoint_ref)
        return request.make_response_result(route_rec_list=list(route_rec_set))


class ThisModule(Module):

    def __init__(self, module_name, services, config):
        super().__init__(module_name)
        iface_type_ref = services.types.reverse_resolve(htypes.hyper_ref.route_resolver)
        service = htypes.hyper_ref.service(ROUTE_RESOLVER_SERVICE_ID, iface_type_ref)
        service_ref = services.ref_registry.distil(service)
        services.service_registry.register(service_ref, RouteResolverService, services.route_resolver)
        ref_collector = services.ref_collector_factory()
        bundle = ref_collector.make_bundle([service_ref])
        ref_path = LOCAL_ROUTE_RESOLVER_REF_PATH
        save_bundle_to_file(bundle, ref_path)
        log.info('Route resolver ref is saved to %s', ref_path)
