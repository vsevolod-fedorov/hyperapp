import os.path
import traceback
import time
import select
from ..common.interface.code_repository import ModuleDep
from ..common.transport_packet import encode_transport_packet, decode_transport_packet
from ..common.tcp_packet import has_full_tcp_packet, decode_tcp_packet, encode_tcp_packet
from .transport import transport_registry


PACKET_ENCODING = 'cdr'
NOTIFICATION_DELAY_TIME = 1  # sec
RECV_SIZE = 4096


class Error(Exception): pass


class TcpConnection(object):

    def __init__( self, socket ):
        self.socket = socket
        self.recv_buf = ''

    def close( self ):
        self.socket.close()

    def send( self, contents ):
        data = encode_tcp_packet(contents)
        ofs = 0
        while ofs < len(data):
            sent_size = self.socket.send(data[ofs:])
            print '  sent (%d) %s...' % (sent_size, data[ofs:ofs + min(sent_size, 100)])
            if sent_size == 0:
                raise Error('Socket is closed')
            ofs += sent_size

    def receive( self, timeout ):
        while True:
            if has_full_tcp_packet(self.recv_buf): break
            ## print '  receiving...'
            rd, wr, xc = select.select([self.socket], [], [self.socket], timeout)
            if not rd and not xc:
                return None
            chunk = self.socket.recv(RECV_SIZE)
            print '  received (%d) %s...' % (len(chunk), chunk[:100])
            if chunk == '':
                raise Error('Socket is closed')
            self.recv_buf += chunk
        packet_data, packet_size = decode_tcp_packet(self.recv_buf)
        self.recv_buf = self.recv_buf[packet_size:]
        ## print 'received:'
        ## pprint.pprint(json_data)
        return packet_data


class TcpClient(object):

    def __init__( self, server, tcp_server, socket, addr, on_close ):
        self.server = server
        self.tcp_server = tcp_server
        self.conn = TcpConnection(socket)
        self.addr = addr
        self.on_close = on_close
        self.stop_flag = False

    def send_update( self, update ):
        self.updates_queue.put(update)

    def stop( self ):
        self.stop_flag = True

    def serve( self ):
        try:
            while not self.stop_flag:
                packet_data = self.conn.receive(NOTIFICATION_DELAY_TIME)
                if not packet_data:  # receive timed out
                    ## if not self.updates_queue.empty():
                    ##     self._send_notification()
                    continue
                self._process_packet(packet_data)
        except Error as x:
            print x
        except:
            traceback.print_exc()
        self.conn.close()
        self.on_close(self)

    def _process_packet( self, data ):
        transport_packet = decode_transport_packet(data)
        print '%r packet from %s:%d:' % (transport_packet.transport_id, self.addr[0], self.addr[1])
        response_data = transport_registry.process_packet(self.server, self.tcp_server, transport_packet)
        if response_data is None:
            print 'no response'
            return None
        print '%d bytes to %s:%d' % (len(response_data), self.addr[0], self.addr[1])
        response_transport_packet = encode_transport_packet(transport_packet.transport_id, response_data)
        self.conn.send(response_transport_packet)
