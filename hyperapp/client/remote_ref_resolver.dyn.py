import logging

from hyperapp.client.module import ClientModule
from .local_server_paths import LOCAL_REF_RESOLVER_REF_PATH, load_bundle_from_file
from .async_ref_resolver import AsyncRefSource

log = logging.getLogger(__name__)


class RemoteRefResolver(AsyncRefSource):

    @classmethod
    async def from_ref(cls, service_ref, ref_registry, proxy_factory):
        proxy = await proxy_factory.from_ref(service_ref)
        return cls(ref_registry, proxy)

    def __init__(self, ref_registry, proxy):
        self._ref_registry = ref_registry
        self._proxy = proxy

    async def resolve_ref(self, ref):
        result = await self._proxy.resolve_ref(ref)
        self._ref_registry.register_capsule(result.capsule)  # cache it locally
        return result.capsule


class ThisModule(ClientModule):

    def __init__(self, module_name, services, config):
        super().__init__(module_name, services)

    async def async_init(self, services):
        service_ref = self._load_ref_resolver_ref(services.unbundler)
        remote_ref_resolver = await RemoteRefResolver.from_ref(service_ref, services.ref_registry, services.proxy_factory)
        services.async_ref_resolver.add_async_source(remote_ref_resolver)

    def _load_ref_resolver_ref(self, unbundler):
        bundle = load_bundle_from_file(LOCAL_REF_RESOLVER_REF_PATH)
        unbundler.register_bundle(bundle)
        assert len(bundle.roots) == 1
        return bundle.roots[0]
