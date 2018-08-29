from ..common.interface import hyper_ref as href_types
from ..common.ref import LOCAL_TRANSPORT_REF
from ..common.route_resolver import RouteSource
from .module import ClientModule


MODULE_NAME = 'endpoint_registry'


class EndpointRegistry(object):

    def __init__(self, ref_registry):
        self._ref_registry = ref_registry
        self._endpoint_set = set()

    def register_endpoint(self, endpoint):
        endpoint_ref = self._ref_registry.register_object(endpoint)
        self.register_endpoint_ref(endpoint_ref)
        return endpoint_ref

    def register_endpoint_ref(self, endpoint_ref):
        self._endpoint_set.add(endpoint_ref)

    def is_registered(self, endpoint_ref):
        return endpoint_ref in self._endpoint_set


class LocalRouteSource(RouteSource):

    def __init__(self, endpoint_registry):
        self._endpoint_registry = endpoint_registry

    def resolve(self, endpoint_ref):
        if self._endpoint_registry.is_registered(endpoint_ref):
            return {LOCAL_TRANSPORT_REF}
        else:
            return set()


class ThisModule(ClientModule):

    def __init__(self, services):
        super().__init__(MODULE_NAME, services)
        services.endpoint_registry = endpoint_registry = EndpointRegistry(services.ref_registry)
        services.route_resolver.add_source(LocalRouteSource(endpoint_registry))
