from .code.mark import mark
from .services import (
    web,
    )


class RemotePeerWebSource:

    def __init__(self, identity, peer):
        self._identity = identity
        self._peer = peer

    def pull(self, ref):
        assert 0, (self._identity, self._peer, ref)


@mark.init_hook
def init_local_server_web_source(peer_list_reg, client_identity):
    peer = peer_list_reg.get('localhost')
    web.add_source(RemotePeerWebSource(client_identity, peer))
