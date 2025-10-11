from .code.mark import mark
from .services import (
    mosaic,
    web,
    )


class RemotePeerWebSource:

    def __init__(self, service_call_factory, identity, peer):
        self._service_call_factory = service_call_factory
        self._identity = identity
        self._peer = peer

    def pull(self, ref):
        rpc_call = self._service_call_factory(self._peer, self._identity, 'web_source')
        _unused_ref = rpc_call(ref=ref)
        # Resolved capsule is pulled to result bundle by returned ref and populated into mosaic on unbundling.
        try:
            return mosaic.resolve_ref(ref).capsule
        except KeyError:
            return None


@mark.init_hook
def init_local_server_web_source(service_call_factory, peer_list_reg, client_identity):
    peer = peer_list_reg.get('localhost')
    web.add_source(RemotePeerWebSource(service_call_factory, client_identity, peer))
