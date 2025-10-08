import logging
from functools import cached_property

from . import htypes
from .services import (
    mosaic,
    web,
    )
from .code.mark import mark
from .code.list_adapter import IndexListAdapterMixin, FnListAdapterBase

log = logging.getLogger(__name__)


class GitLogAdapter(FnListAdapterBase, IndexListAdapterMixin):

    @classmethod
    @mark.actor.ui_adapter_creg
    def from_piece(cls, piece, model, ctx,
                   accessor_creg, system_fn_creg, rpc_system_call_factory,
                   client_feed_factory, column_visible_reg, peer_creg):
        accessor = accessor_creg.invite(piece.accessor, model, ctx)
        my_model = accessor.get_value()
        fn = system_fn_creg.invite(piece.system_fn)
        remote_peer, real_model = cls._resolve_model(peer_creg, my_model)
        assert isinstance(real_model, htypes.git.log_model)
        return cls(system_fn_creg, rpc_system_call_factory, client_feed_factory, column_visible_reg,
                   my_model, real_model, remote_peer, ctx, fn)

    def __init__(self, system_fn_creg, rpc_system_call_factory, client_feed_factory, column_visible_reg,
                 model, real_model, remote_peer, ctx, fn):
        super().__init__(column_visible_reg, real_model, item_t=htypes.git.log_item)
        self._system_fn_creg = system_fn_creg
        self._rpc_system_call_factory = rpc_system_call_factory
        self._remote_peer = remote_peer
        self._ctx = ctx
        self._fn = fn
        self._commit_list = []
        self._items = []
        try:
            self._feed = client_feed_factory(model, ctx)
        except KeyError:
            self._feed = None
        else:
            self._feed.subscribe(self)

    def row_count(self):
        return self._data.commit_count

    def get_item(self, idx):
        self._ensure_item_loaded(idx)
        return self._items[idx]

    @staticmethod
    def _commit_to_item(commit):
        return htypes.git.log_item(
            id_short=commit.short_id,
            dt=commit.time,
            author=commit.author,
            message=commit.message,
            )

    @cached_property
    def _data(self):
        kw = {
            'model': self._real_model,
            'piece': self._real_model,
            }
        if self._remote_peer:
            rpc_call = self._rpc_system_call_factory(
                receiver_peer=self._remote_peer,
                sender_identity=self._ctx.identity,
                fn=self._fn,
                )
            call_kw = self._fn.call_kw(self._ctx, **kw)
            return rpc_call(**call_kw)
        else:
            return self._fn.call(self._ctx, **kw)

    def _ensure_item_loaded(self, idx):
        if idx < len(self._items):
            return
        if idx == 0:
            commit = web.summon(self._data.head_commit)
            self._commit_list.append(commit)
            self._items.append(self._commit_to_item(commit))
            return
        while len(self._items) - 1 < idx:
            last_commit = self._commit_list[-1]
            assert last_commit.parents  # Actual commit count does not match data commit_count.
            commit = web.summon(last_commit.parents[0])
            self._commit_list.append(commit)
            self._items.append(self._commit_to_item(commit))


# TODO: Add support for model_tt view_factory with system_fn.
@mark.view_factory.ui_t
def git_log_layout(piece, accessor, system_fn):
    adapter = htypes.git.log_adapter(
        accessor=mosaic.put(accessor),
        system_fn=mosaic.put(system_fn.piece),
        )
    return htypes.list.view(
        adapter=mosaic.put(adapter),
        )
