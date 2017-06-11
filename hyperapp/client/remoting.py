import logging
import asyncio
import abc
from ..common.util import is_list_inst, encode_path, encode_route
from ..common.htypes import tServerRoutes
from ..common.visual_rep import pprint
from ..common.packet_coders import packet_coders
from ..common.server_public_key_collector import ServerPksCollector
from ..common.identity import PublicKey
from ..common.url import Url, UrlWithRoutes
from ..common.transport_packet import tTransportPacket
from ..common.route_storage import RouteStorage
from .request import Request, ClientNotification, Response
from .module_manager import ModuleManager
from .proxy_registry import ProxyRegistry

log = logging.getLogger(__name__)


class Transport(metaclass=abc.ABCMeta):

    def __init__(self, services):
        self._request_types = services.request_types
        self._resource_types = services.types.resource
        self._packet_types = services.types.packet
        self._module_manager = services.module_manager
        self._iface_registry = services.iface_registry
        self._type_module_repository = services.type_module_repository
        self._route_storage = services.route_storage
        self._objimpl_registry = services.objimpl_registry
        self._view_registry = services.view_registry
        self._param_editor_registry = services.param_editor_registry
        self._code_repository = services.code_repository
        self._identity_controller = services.identity_controller
        self._resources_manager = services.resources_manager
        assert isinstance(self._module_manager, ModuleManager), repr(self._module_manager)
        ## assert isinstance(code_repository, CodeRepository), repr(code_repository)  # circular import dep
        ## assert isinstance(self._identity_controller, IdentityController), repr(self._identity_controller)  # from dynamic module

    @asyncio.coroutine
    def process_aux_info(self, aux_info):
        assert isinstance(aux_info, self._packet_types.aux_info), repr(aux_info)
        self._add_type_modules(aux_info.type_modules)  # types must be added before requirements - modules may use them
        yield from self._resolve_requirements(aux_info.requirements)
        self._add_routes(aux_info.routes)
        self._resources_manager.register(aux_info.resources)
        
    @asyncio.coroutine
    def _resolve_requirements(self, requirements):
        assert is_list_inst(requirements, self._packet_types.requirement), repr(requirements)
        unfulfilled_requirements = list(filter(self._is_unfulfilled_requirement, requirements))
        if not unfulfilled_requirements: return
        type_modules, code_modules, resources = yield from self._code_repository.get_modules_by_requirements(unfulfilled_requirements)
        self._add_type_modules(type_modules or [])  # modules is None if there is no code repositories
        self._module_manager.load_code_module_list(code_modules or [])  # modules is None if there is no code repositories
        self._resources_manager.register(resources or [])
        
    def _is_unfulfilled_requirement(self, requirement):
        registry, key = requirement
        if registry == 'object':
            return not self._objimpl_registry.is_registered(key)
        if registry == 'handle':
            return not self._view_registry.is_registered(key)
        if registry == 'interface':
            return not self._iface_registry.is_registered(key)
        if registry == 'param_editor':
            return not self._param_editor_registry.is_registered(key)
        if registry == 'class':
            return False
        if registry == 'resources':
            return False
        assert False, repr(registry)  # Unknown registry

    def _add_type_modules(self, type_modules):
        for type_module in type_modules:
            log.info('received type module %r with %d typedefs, provided %r',
                      type_module.module_name, len(type_module.typedefs),
                      ', '.join('%s:%s' % (rec.hierarchy_id, rec.class_id) for rec in type_module.provided_classes))
            if not self._type_module_repository.has_type_module(type_module.module_name):
                self._type_module_repository.add_type_module(type_module)

    def _add_routes(self, routes):
        for srv_routes in routes:
            public_key = PublicKey.from_der(srv_routes.public_key_der)
            log.info('received routes for %s: %s',
                     public_key.get_short_id_hex(), ', '.join(encode_route(route) for route in srv_routes.routes))
            self._route_storage.add_routes(public_key, srv_routes.routes)

    def make_request_packet(self, encoding, request_or_notification):
        server_pks = ServerPksCollector().collect_public_key_ders(self._request_types.tClientPacket, request_or_notification.to_data())
        routes = [tServerRoutes(pk, self._route_storage.get_routes(PublicKey.from_der(pk))) for pk in server_pks]
        aux_info = self._packet_types.aux_info(requirements=[], type_modules=[], modules=[], routes=routes, resources=[])
        payload = packet_coders.encode(encoding, request_or_notification.to_data(), self._request_types.tClientPacket)
        return self._packet_types.packet(aux_info, payload)

    @asyncio.coroutine
    @abc.abstractmethod
    def send_request_rec(self, remoting, public_key, route, request_or_notification):
        pass

    @asyncio.coroutine
    @abc.abstractmethod
    def process_packet(self, protocol, session_list, server_public_key, data):
        pass


class TransportRegistry(object):

    def __init__(self):
        self._id2transport = {}

    def register(self, id, transport):
        assert isinstance(id, str), repr(id)
        assert isinstance(transport, Transport), repr(transport)
        self._id2transport[id] = transport

    def resolve(self, id):
        return self._id2transport[id]


class Remoting(object):

    def __init__(self, request_types, resource_types, packet_types, route_storage, proxy_registry):
        assert isinstance(route_storage, RouteStorage), repr(route_storage)
        assert isinstance(proxy_registry, ProxyRegistry), repr(proxy_registry)
        self.transport_registry = TransportRegistry()
        self._request_types = request_types
        self._resource_types = resource_types
        self._packet_types = packet_types
        self._route_storage = route_storage
        self._proxy_registry = proxy_registry
        self._futures = {}  # request id -> future for response

    def add_routes(self, public_key, routes):
        self._route_storage.add_routes(public_key, routes)

    def add_routes_from_url(self, url):
        assert isinstance(url, UrlWithRoutes), repr(url)
        self.add_routes(url.public_key, url.routes)

    def add_routes_to_url(self, url):
        assert isinstance(url, Url), repr(url)
        return url.clone_with_routes(self._route_storage.get_routes(url.public_key))

    @asyncio.coroutine
    def execute_request(self, public_key, request):
        assert isinstance(public_key, PublicKey), repr(public_key)
        assert isinstance(request, Request), repr(request)
        self._futures[request.request_id] = future = asyncio.Future()
        try:
            yield from self.send_request_or_notification(public_key, request)
            return (yield from future)
        finally:
            del self._futures[request.request_id]

    @asyncio.coroutine
    def send_notification(self, public_key, notification):
        assert isinstance(public_key, PublicKey), repr(public_key)
        assert isinstance(notification, ClientNotification), repr(notification)
        yield from self.send_request_or_notification(public_key, notification)

    @asyncio.coroutine
    def send_request_or_notification(self, public_key, request_or_notification):
        pprint(self._request_types.tClientPacket, request_or_notification.to_data(), self._resource_types, self._packet_types)
        for route in self._route_storage.get_routes(public_key) or []:
            transport_id = route[0]
            transport = self.transport_registry.resolve(transport_id)
            if not transport:
                log.info('Warning: unknown transport: %r', transport_id)
                continue
            try:
                return (yield from transport.send_request_rec(self, public_key, route[1:], request_or_notification))
            except:
                # todo: catch specific exceptions; try next route
                raise
        raise RuntimeError('Unable to send packet to %s - no reachable transports'
                           % public_key.get_short_id_hex())

    @asyncio.coroutine
    def process_packet(self, protocol, session_list, server_public_key, packet):
        assert isinstance(packet, tTransportPacket), repr(packet)
        log.info('received %r packet, contents %d bytes', packet.transport_id, len(packet.data))
        transport = self.transport_registry.resolve(packet.transport_id)
        response_or_notification = yield from transport.process_packet(protocol, session_list, server_public_key, packet.data)
        if response_or_notification is None:
            return
        self._process_updates(server_public_key, response_or_notification.updates)
        if isinstance(response_or_notification, Response):
            future = self._futures.get(response_or_notification.request_id)
            if future:
                future.set_result(response_or_notification)

    def _process_updates(self, server_public_key, updates):
        for update in updates:
            obj = self._proxy_registry.resolve(server_public_key, update.path)
            if obj:
                obj.process_update(update.diff)
            # otherwize object is already gone and updates must be discarded
