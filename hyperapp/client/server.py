from PySide import QtCore
from ..common.util import is_list_inst, encode_url, decode_url
from ..common.packet import Packet
from ..common.endpoint import Endpoint
from ..common.visual_rep import pprint
from ..common.interface import tClientPacket, Interface, iface_registry
from .request import ClientNotification, Request, ResponseBase, Response
from .objimpl_registry import objimpl_registry
from .proxy_registry import proxy_registry
from .transport import transports


PACKET_ENCODING = 'cdr'


class Url(object):

    def __init__( self, endpoint, path ):
        assert isinstance(endpoint, Endpoint), repr(endpoint)
        assert is_list_inst(path, basestring), repr(path)
        self.endpoint = endpoint
        self.path = path


class RespHandler(object):

    def __init__( self, iface, command_id ):
        assert isinstance(iface, Interface), repr(iface)
        assert isinstance(command_id, basestring), repr(command_id)
        self.iface = iface
        self.command_id = command_id

    def process_response( self, server, response ):
        raise NotImplementedError(self.__class__)


class Server(object):

    _servers = {}  # public key -> Server

    @classmethod
    def produce( cls, endpoint ):
        assert isinstance(endpoint, Endpoint), repr(endpoint)
        server = cls._servers.get(endpoint.public_key)
        if not server:
            server = Server(endpoint)
            cls._servers[endpoint.public_key] = server
        return server

    @classmethod
    def resolve_url( cls, url ):
        assert isinstance(url, Url), repr(url)
        return (cls.produce(url.endpoint), url.path)

    def __init__( self, endpoint ):
        assert isinstance(endpoint, Endpoint), repr(endpoint)
        self.endpoint = endpoint
        self.pending_requests = {}  # request_id -> RespHandler
        self.id = self.endpoint.public_key.make_id().encode('hex')

    def get_endpoint( self ):
        return self.endpoint

    def get_id( self ):
        return self.id

    def make_url( self, path ):
        return Url(self.endpoint, path)

    def __repr__( self ):
        return 'server:%s' % self.endpoint

    def resolve_object( self, objinfo ):
        return objimpl_registry.produce_obj(self, objinfo)

    def send_notification( self, notification ):
        assert isinstance(notification, ClientNotification), repr(notification)
        print 'send_notification', notification.command_id, notification
        self._send(notification)

    def execute_request( self, request, resp_handler ):
        assert isinstance(request, Request), repr(request)
        assert isinstance(resp_handler, RespHandler), repr(resp_handler)
        request_id = request.request_id
        assert request_id not in self.pending_requests, repr(request_id)
        print 'execute_request', request.command_id, request_id
        self.pending_requests[request_id] = resp_handler
        self._send(request)

    def _send( self, request ):
        request_rec = request.encode()
        encoding = PACKET_ENCODING
        print '%s packet to %s' % (encoding, self.endpoint)
        pprint(tClientPacket, request_rec)
        packet = Packet.from_contents(encoding, request_rec, tClientPacket)
        transports.send_packet(self, self.endpoint, packet)

    def process_packet( self, packet ):
        print '%r from %s' % (packet, self.endpoint)
        app = QtCore.QCoreApplication.instance()
        app.add_modules(packet.aux.modules)
        if app.has_unfulfilled_requirements(packet.aux.requirements):
            app.request_required_modules_and_reprocess_packet(self, packet)
        else:
            self._process_packet(packet)

    def reprocess_packet( self, packet ):
        print 'reprocessing %r from %s' % (packet, self.endpoint)
        app = QtCore.QCoreApplication.instance()
        app.add_modules(packet.aux.modules)
        assert not app.has_unfulfilled_requirements(packet.aux.requirements)  # still has unfilfilled requirements
        self._process_packet(packet)

    def _process_packet( self, packet ):
        response_or_notification = ResponseBase.from_response_rec(self, iface_registry, packet.decode_server_packet())
        self._process_updates(response_or_notification.updates)
        if isinstance(response_or_notification, Response):
            response = response_or_notification
            print '   response for request', response.command_id, response.request_id
            resp_handler = self.pending_requests.get(response.request_id)
            if not resp_handler:
                print 'Received response #%s for a missing (already destroyed) object, ignoring' % response.request_id
                return
            del self.pending_requests[response.request_id]
            resp_handler.process_response(response, self)

    def _process_updates( self, updates ):
        for update in updates:
            obj = proxy_registry.resolve(self, update.path)
            if obj:
                obj.process_update(update.diff)
            # otherwize object is already gone and updates must be discarded
