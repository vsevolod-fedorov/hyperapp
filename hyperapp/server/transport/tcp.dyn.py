import logging
import threading
import socket
import select
import time
import uuid
from queue import Queue
from functools import partial

from hyperapp.common.htypes import ref_t, route_t
from hyperapp.common.visual_rep import pprint
from hyperapp.common.ref import LOCAL_TRANSPORT_REF, ref_repr, ref_list_repr
from hyperapp.common.module import Module
from . import htypes
from .tcp_packet import has_full_tcp_packet, encode_tcp_packet, decode_tcp_packet
from .route_resolver import RouteRegistry

log = logging.getLogger(__name__)


DEFAULT_BIND_ADDRESS = ('localhost', 0)
STOP_DELAY_TIME_SEC = 0.3
NOTIFICATION_DELAY_TIME_SEC = 1
RECV_SIZE = 4096
TCP_PACKET_ENCODING = 'cdr'


class SocketClosedError(Exception):

    def __init__(self):
        super().__init__('Socket is closed by remote peer')


class TcpChannel(object):

    def __init__(self, socket):
        self.socket = socket
        self.recv_buf = b''

    def close(self):
        self.socket.close()

    def send(self, bundle):
        data = encode_tcp_packet(bundle, TCP_PACKET_ENCODING)
        ofs = 0
        while ofs < len(data):
            sent_size = self.socket.send(data[ofs:])
            log.debug('  sent (%d) %s...', sent_size, data[ofs:ofs + min(sent_size, 100)])
            if sent_size == 0:
                raise SocketClosedError()
            ofs += sent_size

    def receive(self, timeout_sec):
        while not has_full_tcp_packet(self.recv_buf):
            ## print '  receiving...'
            rd, wr, xc = select.select([self.socket], [], [self.socket], timeout_sec)
            if not rd and not xc:
                return None
            chunk = self.socket.recv(RECV_SIZE)
            log.debug('  received (%d) %s...', len(chunk), chunk[:100])
            if chunk == b'':
                raise SocketClosedError()
            self.recv_buf += chunk
        bundle, packet_size = decode_tcp_packet(self.recv_buf)
        self.recv_buf = self.recv_buf[packet_size:]
        return bundle


class TcpClient(object):

    def __init__(
            self,
            types,
            mosaic,
            route_resolver,
            ref_collector_factory,
            unbundler,
            remoting,
            tcp_server,
            outcoming_queue,
            peer_address,
            socket,
            on_failure,
            ):
        self._types = types
        self._mosaic = mosaic
        self._route_resolver = route_resolver
        self._ref_collector_factory = ref_collector_factory
        self._unbundler = unbundler
        self._remoting = remoting
        self._tcp_server = tcp_server
        self._outcoming_queue = outcoming_queue
        self._peer_address = peer_address
        self._on_failure = on_failure
        self._connection_id = str(uuid.uuid4())
        self._channel = TcpChannel(socket)
        self._stop_flag = False
        self._thread = threading.Thread(target=self._thread_main)
        self._my_route_registry = RouteRegistry()
        self._my_address_ref = None

    def __str__(self):
        s = 'tcp: client %s:%d' % (self._peer_address[0], self._peer_address[1])
        if self._my_address_ref:
            s += ' ' + ref_repr(self._my_address_ref)
        return s

    @property
    def id(self):
        return self._connection_id

    def start(self):
        address = htypes.tcp_transport.incoming_connection_address(connection_id=self._connection_id)
        self._my_address_ref = self._mosaic.distil(address)
        self._log('Incoming connection address: %s', address)
        self._route_resolver.add_source(self._my_route_registry)
        self._thread.start()

    def stop(self):
        self._route_resolver.remove_source(self._my_route_registry)
        self._stop_flag = True

    def join(self):
        self._thread.join()

    def _thread_main(self):
        self._log('started')
        try:
            while not self._stop_flag:
                self._receive_and_process_bundle()
                self._send_outcoming_messages()
        except SocketClosedError:
            self._log('connection is closed by remote peer')
        except Exception as x:
            log.exception('Tcp client thread is failed')
            self._on_failure('Tcp client thread is failed: %r' % x)
        self._channel.close()
        self._tcp_server.client_finished(self)
        self._log('finished')

    def _receive_and_process_bundle(self):
        bundle = self._channel.receive(NOTIFICATION_DELAY_TIME_SEC)
        if bundle:  # receive timed out otherwise
            self._process_incoming_bundle(bundle)

    def _process_incoming_bundle(self, bundle):
        self._log('Received bundle with roots %s', ref_list_repr(bundle.roots))
        pprint(bundle, title='incoming bundle', logger=partial(self._log, level=logging.DEBUG))
        self._unbundler.register_bundle(bundle)
        self._register_incoming_routes(bundle.route_list)
        for rpc_request_ref in bundle.roots:
            rpc_request = self._types.resolve_ref(rpc_request_ref, expected_type=htypes.hyper_ref.rpc_message).value
            self._remoting.process_rpc_request(rpc_request_ref, rpc_request)

    def _register_incoming_routes(self, route_list):
        for route in route_list:
            if route.transport_ref == LOCAL_TRANSPORT_REF:
                self._my_route_registry.register(
                    route_t(route.endpoint_ref, self._my_address_ref, route.available_at))

    def _send_outcoming_messages(self):
        while not self._outcoming_queue.empty():
            self._send_message(self._outcoming_queue.get())

    def _send_message(self, message_ref):
        ref_collector = self._ref_collector_factory()
        bundle = ref_collector.make_bundle([message_ref])
        self._log('Sending bundle with roots %s', ref_list_repr(bundle.roots))
        pprint(bundle, title='outgoing bundle', logger=partial(self._log, level=logging.DEBUG))
        self._channel.send(bundle)

    def _log(self, message, *args, level=logging.INFO):
        log.log(level, '%s: %s' % (self, message), *args)


class TcpServer(object):

    def __init__(
            self,
            types,
            mosaic,
            route_resolver,
            ref_collector_factory,
            unbundler,
            remoting,
            local_transport_ref_set,
            bind_address,
            on_failure,
            ):
        self._types = types
        self._mosaic = mosaic
        self._route_resolver = route_resolver
        self._ref_collector_factory = ref_collector_factory
        self._unbundler = unbundler
        self._remoting = remoting
        self._bind_address = bind_address  # (host, port)
        self._on_failure = on_failure
        self._listen_thread = threading.Thread(target=self._main)
        self._stop_flag = False
        self._id2outcoming_queue = {}
        self._id2client = {}
        self._finished_client_set = set()
        self._client_lock = threading.Lock()
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.bind(self._bind_address)
        self._sock_address = self._socket.getsockname()
        address = htypes.tcp_transport.address(self._sock_address[0], self._sock_address[1])
        tcp_transport_ref = self._mosaic.distil(address)
        local_transport_ref_set.add(tcp_transport_ref)

    def start(self):
        log.info('Tcp transport: listening on %s:%d' % self._sock_address)
        self._socket.listen(5)
        self._listen_thread.start()

    def stop(self):
        if self._stop_flag:
            log.info('tcp: already stopping')
            return
        log.info('tcp: stopping...')
        self._stop_flag = True
        if self._listen_thread.is_alive():
            self._listen_thread.join()
        log.info('tcp: listening thread is joined.')
        for client in self._id2client.values():
            client.stop()
        while True:
            with self._client_lock:
                if not self._id2client:
                    break
            self._join_finished_clients()
            time.sleep(0.1)
        log.info('tcp: stopped.')

    def get_outcoming_queue(self, client_id):
        return self._id2outcoming_queue[client_id]

    def client_finished(self, client):
        with self._client_lock:
            assert client.id in self._id2client
            self._finished_client_set.add(client)

    def _main(self):
        try:
            self._accept_loop()
        except:
            log.exception('Tcp server thread is failed:')
            self._stop_flag = True
        log.debug('tcp: listening thread is stopped.')

    def _accept_loop(self):
        while not self._stop_flag:
            rd, wr, err = select.select([self._socket], [], [self._socket], STOP_DELAY_TIME_SEC)
            if rd or err:
                channel_socket, peer_address = self._socket.accept()
                log.info('tcp: accepted connection from %s:%d' % peer_address)
                outcoming_queue = Queue()
                client = TcpClient(
                    self._types,
                    self._mosaic,
                    self._route_resolver,
                    self._ref_collector_factory,
                    self._unbundler,
                    self._remoting,
                    self,
                    outcoming_queue,
                    peer_address,
                    channel_socket,
                    self._on_failure,
                    )
                client.start()
                self._id2outcoming_queue[client.id] = outcoming_queue
                self._id2client[client.id] = client
            self._join_finished_clients()

    def _join_finished_clients(self):
        with self._client_lock:
            for client in self._finished_client_set:
                client.join()
                del self._id2client[client.id]
                del self._id2outcoming_queue[client.id]
            self._finished_client_set.clear()


class IncomingConnectionTransport(object):

    def __init__(self, address, server):
        self._queue = server.get_outcoming_queue(address.connection_id)

    def send(self, message_ref):
        assert isinstance(message_ref, ref_t), repr(message_ref)
        self._queue.put(message_ref)

        
class ThisModule(Module):

    def __init__(self, module_name, services, config):
        super().__init__(module_name)
        bind_address = None
        if config:
            bind_address = config.get('bind_address')
        if not bind_address:
            bind_address = DEFAULT_BIND_ADDRESS
        self.server = server = TcpServer(
            services.types,
            services.mosaic,
            services.route_resolver,
            services.ref_collector_factory,
            services.unbundler,
            services.remoting,
            services.local_transport_ref_set,
            bind_address=bind_address,
            on_failure=services.failed,
            )
        services.transport_registry.register_actor(
            htypes.tcp_transport.incoming_connection_address, IncomingConnectionTransport, server)
        services.on_start.append(self.server.start)
        services.on_stop.append(self.server.stop)
