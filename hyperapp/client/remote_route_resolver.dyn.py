import logging
import asyncio

from ..common.local_server_paths import LOCAL_ROUTE_RESOLVER_REF_PATH, load_bundle_from_file
from .async_route_resolver import AsyncRouteSource
from .module import ClientModule

log = logging.getLogger(__name__)


MODULE_NAME = 'remote_route_resolver'


class RemoteRouteResolver(AsyncRouteSource):

    @classmethod
    async def from_ref(cls, service_ref, route_registry, proxy_factory):
        proxy = await proxy_factory.from_ref(service_ref)
        return cls(route_registry, proxy)

    def __init__(self, route_registry, proxy):
        self._route_registry = route_registry
        self._proxy = proxy
        self._recursion_lock = asyncio.Lock()

    async def resolve(self, endpoint_ref):
        with (await self._recursion_lock):
            result = await self._proxy.resolve_route(endpoint_ref)
            # cache received routes
            for transport_ref in result.transport_ref_list:
                self._route_registry.register(endpoint_ref, transport_ref)
                return set(result.transport_ref_list)


class ThisModule(ClientModule):

    def __init__(self, services):
        super().__init__(MODULE_NAME, services)

    async def async_init(self, services):
        service_ref = self._load_route_resolver_ref(services.unbundler)
        remote_route_resolver = await RemoteRouteResolver.from_ref(service_ref, services.route_registry, services.proxy_factory)
        services.async_route_resolver.add_async_source(remote_route_resolver)

    def _load_route_resolver_ref(self, unbundler):
        bundle = load_bundle_from_file(LOCAL_ROUTE_RESOLVER_REF_PATH)
        unbundler.register_bundle(bundle)
        assert len(bundle.roots) == 1
        return bundle.roots[0]
