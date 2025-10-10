from .code.mark import mark


@mark.init_hook
def init_local_server_web_source(peer_list_reg, client_identity):
    peer = peer_list_reg.get('localhost')
    assert 0, client_identity
