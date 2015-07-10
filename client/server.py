from PySide import QtNetwork
from common.packet import Packet
from common.json_decoder import JsonDecoder
from common.json_encoder import JsonEncoder
from common.interface import Interface, iface_registry
from common.request import tServerPacket, tClientPacket, ClientNotification, Request, ServerNotification, Response
import proxy_registry
from proxy_object import ProxyListObject


PACKET_ENCODING = 'json'


class Connection(object):

    addr2connection = {}

    @classmethod
    def get_connection( cls, addr ):
        connection = cls.addr2connection.get(addr)
        if not connection:
            connection = Connection(addr)
            cls.addr2connection[addr] = connection
        return connection

    def __init__( self, addr ):
        self.addr = addr
        self.socket = None
        self.connected = False
        self.send_buf = ''
        self.recv_buf = ''
        host, port = self.addr
        print 'Network: connecting to %s:%d' % (host, port)
        self.socket = QtNetwork.QTcpSocket()
        self.socket.error.connect(self.on_error)
        self.socket.stateChanged.connect(self.on_state_changed)
        self.socket.hostFound.connect(self.on_host_found)
        self.socket.connected.connect(self.on_connected)
        self.socket.bytesWritten.connect(self.on_bytes_written)
        self.socket.readyRead.connect(self.on_ready_read)
        self.socket.connectToHost(host, port)

    def trace( self, msg ):
        host, port = self.addr
        print 'Network, connection to %s:%d: %s' % (host, port, msg)

    def on_error( self, msg ):
        self.trace('Error: %s' % msg)

    def on_state_changed( self, state ):
        self.trace('State changed: %r' % state)

    def on_host_found( self ):
        self.trace('Host found')

    def on_connected( self ):
        self.trace('Connected, %d bytes in send buf' % len(self.send_buf))
        self.connected = True
        if self.send_buf:
            self.socket.write(self.send_buf)

    def on_bytes_written( self, size ):
        self.send_buf = self.send_buf[size:]
        self.trace('%d bytes is written, %d bytes to go' % (size, len(self.send_buf)))
        if self.send_buf:
            self.socket.write(self.send_buf)

    def on_ready_read( self ):
        data = str(self.socket.readAll())
        self.trace('%d bytes is received: %s' % (len(data), data))
        self.recv_buf += data
        while Packet.is_full(self.recv_buf):
            packet, self.recv_buf = Packet.decode(self.recv_buf)
            self.trace('received %s packet (%d bytes remainder): %s'
                       % (packet.encoding, len(self.recv_buf), packet.contents))
            self.process_packet(packet)
            
    def process_packet( self, packet ):
        print 'processing %s packet: %s' % (packet.encoding, packet.contents)
        server = Server(self.addr)
        decoder = JsonDecoder(server, iface_registry, server.resolve_object)
        response = decoder.decode(tServerPacket, packet.contents)
        if isinstance(response, Response):
            proxy_registry.process_received_response(response)
        else:
            assert isinstance(response, ServerNotification), repr(response)
            proxy_registry.process_received_notification(response)

    def send_data( self, data ):
        self.trace('sending data, old=%d, write=%d, new=%d' % (len(self.send_buf), len(data), len(self.send_buf) + len(data)))
        if self.connected and not self.send_buf:
            self.socket.write(data)
        self.send_buf += data  # may be sent partially, will send remainder on bytesWritten signal

    def __del__( self ):
        print '~Connection', self.addr


class Server(object):

    def __init__( self, addr ):
        self.addr = addr

    def resolve_object( self, objinfo ):
        obj_ctr = proxy_registry.resolve_iface(objinfo.proxy_id)
        return obj_ctr(self, objinfo.path, objinfo.iface, objinfo.contents)

    def send_notification( self, request ):
        assert isinstance(request, ClientNotification), repr(request)
        print 'send_notification', request
        json_data = JsonEncoder().encode(tClientPacket, request)
        packet_data = Packet(PACKET_ENCODING, json_data).encode()
        Connection.get_connection(self.addr).send_data(packet_data)

    def execute_request( self, request, resp_handler ):
        assert isinstance(request, Request), repr(request)
        request_id = request.request_id
        print 'execute_request', request_id, request
        proxy_registry.register_resp_handler(request_id, resp_handler)
        json_data = JsonEncoder().encode(tClientPacket, request)
        packet_data = Packet(PACKET_ENCODING, json_data).encode()
        Connection.get_connection(self.addr).send_data(packet_data)
