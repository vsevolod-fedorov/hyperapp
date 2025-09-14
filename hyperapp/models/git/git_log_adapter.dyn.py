import logging
from functools import cached_property

from . import htypes
from .services import (
    mosaic,
    )
from .code.mark import mark
from .code.list_adapter import IndexListAdapterMixin, FnListAdapterBase

log = logging.getLogger(__name__)


class GitLogAdapter(FnListAdapterBase, IndexListAdapterMixin):

    @classmethod
    @mark.actor.ui_adapter_creg
    def from_piece(cls, piece, model, ctx,
                   accessor_creg, system_fn_creg, client_feed_factory, column_visible_reg, peer_creg):
        accessor = accessor_creg.invite(piece.accessor, model, ctx)
        my_model = accessor.get_value()
        fn = system_fn_creg.invite(piece.system_fn)
        _unused_remote_peer, real_model = cls._resolve_model(peer_creg, my_model)
        assert isinstance(real_model, htypes.git.log_model)
        return cls(system_fn_creg, client_feed_factory, column_visible_reg,
                   my_model, real_model, ctx, fn)

    def __init__(self, system_fn_creg, client_feed_factory, column_visible_reg,
                 model, real_model, ctx, fn):
        super().__init__(column_visible_reg, real_model, item_t=htypes.git.log_item)
        self._system_fn_creg = system_fn_creg
        self._ctx = ctx
        self._fn = fn
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

    @cached_property
    def _data(self):
        kw = {
            'model': self._real_model,
            'piece': self._real_model,
            }
        return self._fn.call(self._ctx, **kw)

    def _ensure_item_loaded(self, idx):
        assert 0, (idx, self._data)


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
