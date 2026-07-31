import logging
from collections import defaultdict, namedtuple

from .services import (
    mosaic,
    )

log = logging.getLogger(__name__)


class Transport:

    _Route = namedtuple('_Route', 'route is_internal')

    def __init__(self, bundler, message_size_limit):
        self._bundler = bundler
        self._receiver_peer_to_seen_refs = defaultdict(set)
        self._message_size_limit = message_size_limit
        self._peer_to_routes = defaultdict(set)

    def __repr__(self):
        return f"<Transport: message_size_limit={self._message_size_limit}>"

    def add_internal_route(self, peer, route):
        self._peer_to_routes[peer.piece].add(self._Route(route, is_internal=True))

    def send_message(self, receiver_peer, sender_identity, message):
        log.debug("Send %s to %s from %s", message, receiver_peer, sender_identity)
        seen_refs = self._receiver_peer_to_seen_refs[receiver_peer.piece]
        refs_and_bundle = self._bundler([mosaic.put(message)], seen_refs, size_limit=self._message_size_limit)
        seen_refs |= refs_and_bundle.ref_set
        parcel = receiver_peer.make_parcel(refs_and_bundle.bundle, sender_identity)
        self._send_parcel(receiver_peer, parcel)

    def _send_parcel(self, receiver_peer, parcel):
        routes = self._peer_to_routes.get(receiver_peer.piece, set())
        log.debug("Routes to %s for %s: %s", receiver_peer, parcel, routes)
        if not routes:
            raise RuntimeError(f"No route for peer {receiver_peer}")
        route, *_ = list(routes)  # TODO: Try every route.
        log.debug("Send parcel %s by route %s (all routes: %s)", parcel, route, routes)
        route.send(parcel)


def transport(config, bundler):
    return Transport(bundler, config.message_size_limit)
