import abc
import logging
from collections import defaultdict, namedtuple

from hyperapp.boot.htypes.packet_coders import packet_coders

from .services import (
    mosaic,
    unbundler,
    )
from .code.packet import has_full_packet, encode_packet, decode_packet

log = logging.getLogger(__name__)


class PacketRoute(metaclass=abc.ABCMeta):

    def __init__(self, bundler):
        self._bundler = bundler

    def __repr__(self):
        return f"<{self}>"

    def send(self, parcel, peer_refs):
        parcel_ref = mosaic.put(parcel.piece)
        refs_and_bundle = self._bundler(parcel_ref, peer_refs)
        peer_refs |= refs_and_bundle.ref_set
        data, bundle_size = encode_packet(refs_and_bundle.bundle)
        log.debug("%s: send bundle, bundle size: %.2f KB, packet size: %.2f KB",
                  self, bundle_size/1024, len(data)/1024)
        self._send_packet(data)
        log.debug("%s: parcel is sent: %s", self, parcel_ref)

    @abc.abstractmethod
    def _send_packet(self, data):
        pass


class Connection:

    def __init__(self, transport):
        self._transport = transport
        self._buffer = b''

    def __repr__(self):
        return f"<{self}>"

    def _process_data(self, data):
        self._buffer += data
        while not has_full_packet(self._buffer):
            return
        bundle, packet_size = decode_packet(self._buffer)
        self._buffer = self._buffer[packet_size:]
        log.info("%s: Received bundle, %d bytes: parcel: %s", self, packet_size, bundle.root)
        ref_set = unbundler.register_bundle(bundle)
        self._transport.process_incoming_parcel(bundle.root, ref_set)


class LocalEndpoint:

    _Request = namedtuple('Request', 'local_identity remote_peer')

    def __init__(self, message_creg, identity):
        self._message_creg = message_creg
        self._identity = identity

    def process_parcel(self, parcel, peer_refs):
        parcel.verify()
        bundle = self._identity.decrypt_parcel(parcel)
        ref_set = unbundler.register_bundle(bundle)
        peer_refs |= ref_set
        request = self._Request(self._identity, parcel.sender)
        self._message_creg.invite(bundle.root, request)


class Transport:

    _Route = namedtuple('_Route', 'route is_internal')

    def __init__(self, bundler, parcel_creg, selectors, message_size_limit):
        self._bundler = bundler
        self._parcel_creg = parcel_creg
        self._selectors = selectors
        self._peer_refs = defaultdict(set)
        self._message_size_limit = message_size_limit
        self._peer_to_routes = defaultdict(set)
        self._peer_to_endpoint = {}

    def __repr__(self):
        return f"<Transport: message_size_limit={self._message_size_limit}>"

    def add_endpoint(self, peer, endpoint):
        self._peer_to_endpoint[peer] = endpoint

    def add_internal_route(self, peer, route):
        self._peer_to_routes[peer].add(self._Route(route, is_internal=True))

    def register_connection(self, connection):
        log.debug("Transport: Register connection: %s", connection)
        self._selectors.register(connection)

    def send_message(self, receiver_peer, sender_identity, message):
        log.debug("Send %s to %s from %s", message, receiver_peer, sender_identity)
        peer_refs = self._peer_refs[receiver_peer]
        refs_and_bundle = self._bundler(mosaic.put(message), peer_refs, size_limit=self._message_size_limit)
        peer_refs |= refs_and_bundle.ref_set
        parcel = receiver_peer.make_parcel(refs_and_bundle.bundle, sender_identity)
        self._send_parcel(receiver_peer, parcel, peer_refs)

    def _send_parcel(self, receiver_peer, parcel, peer_refs):
        routes = self._peer_to_routes.get(receiver_peer, set())
        log.debug("Routes to %s for %s: %s", receiver_peer, parcel, routes)
        if not routes:
            raise RuntimeError(f"No route for peer {receiver_peer}")
        rec, *_ = list(routes)  # TODO: Try every route.
        log.debug("Send parcel %s by route %s (all routes: %s)", parcel, rec.route, routes)
        rec.route.send(parcel, peer_refs)

    def process_incoming_parcel(self, parcel_ref, ref_set):
        parcel = self._parcel_creg.invite(parcel_ref)
        peer_refs = self._peer_refs[parcel.receiver]
        peer_refs |= ref_set
        endpoint = self._peer_to_endpoint[parcel.receiver]
        endpoint.process_parcel(parcel, peer_refs)


def transport(config, bundler, parcel_creg, selectors):
    return Transport(bundler, parcel_creg, selectors, config.message_size_limit)
