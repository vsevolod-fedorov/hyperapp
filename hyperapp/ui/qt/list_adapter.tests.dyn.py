from unittest.mock import Mock

from . import htypes
from .services import (
    mosaic,
    )
from .tested.code.list_adapter import (
    IndexListAdapterMixin,
    KeyListAdapterMixin,
    FnListAdapterBase,
    )


class ListAdapterStub(FnListAdapterBase):

    def row_count(self):
        pass

    def get_item(self, idx):
        pass


def test_colunn_types():
    adapter = ListAdapterStub(
        column_visible_reg=Mock(),
        real_model=htypes.list_adapter_tests.sample_list(),
        item_t=htypes.list_adapter_tests.item,
        )
    key = adapter._column_k('id')
    assert key


def test_resolve_model(peer_creg, generate_rsa_identity):
    identity = generate_rsa_identity(fast=True)
    real_model = htypes.list_adapter_tests.sample_list()
    model = htypes.model.remote_model(
        model=mosaic.put(real_model),
        remote_peer=mosaic.put(identity.peer.piece),
        )
    _remote_peer, resolved_model = FnListAdapterBase._resolve_model(peer_creg, model)
    assert resolved_model == real_model


def test_index_list_list_state():
    mixin = IndexListAdapterMixin()
    state = mixin.make_list_state(123)
    assert isinstance(state, htypes.list.state)


def test_key_list_list_state():
    mixin = KeyListAdapterMixin('id', htypes.builtin.string)
    mixin._key_to_idx['some-key'] = 123
    mixin._ensure_populated = lambda: None
    state = mixin.make_list_state('some-key')
    assert isinstance(state, htypes.list.state)
