import uuid

from ..common.htypes import EncodableEmbedded
from ..common.interface import hyper_ref as href_types
from .module import Module


class ProxyMethod(object):

    def __init__(self, ref_registry, transport, iface, service_id, command):
        self._ref_registry = ref_registry
        self._transport = transport
        self._iface = iface
        self._service_id = service_id
        self._command = command

    async def __call__(self, *args, **kw):
        if self._command.is_request:
            request_id = str(uuid.uuid4())
        else:
            request_id = None
        params = self._command.request(*args, **kw)
        request = href_types.service_request(
            iface_full_type_name=self._iface.full_name,
            service_id=self._service_id,
            command_id=self._command.command_id,
            request_id=request_id,
            params=EncodableEmbedded(self._command.request, params),
            )
        request_ref = self._ref_registry.register_object(href_types.service_request, request)
        self._transport.send(request_ref)


class RemotingProxy(object):

    def __init__(self, ref_registry, transport, iface, service_id):
        self._ref_registry = ref_registry
        self._transport = transport
        self._iface = iface
        self._service_id = service_id

    def __getattr__(self, name):
        command = self._iface.get(name)
        if not command:
            raise AttributeError(name)
        return ProxyMethod(self._ref_registry, self._transport, self._iface, self._service_id, command)


class ProxyFactory(object):

    def __init__(self, types, ref_registry, async_ref_resolver, transport_resolver):
        self._types = types
        self._ref_registry = ref_registry
        self._async_ref_resolver = async_ref_resolver
        self._transport_resolver = transport_resolver

    async def from_ref(self, ref):
        service = await self._async_ref_resolver.resolve_ref_to_object(ref, expected_type='hyper_ref.service_ref')
        iface = self._types.resolve(service.iface_full_type_name)
        transport = await self._transport_resolver.resolve(service.transport_ref)
        return RemotingProxy(self._ref_registry, transport, iface, service.service_id)


class ThisModule(Module):

    def __init__(self, services):
        Module.__init__(self, services)
        services.proxy_factory = ProxyFactory(
            services.types,
            services.ref_registry,
            services.async_ref_resolver,
            services.transport_resolver,
            )
