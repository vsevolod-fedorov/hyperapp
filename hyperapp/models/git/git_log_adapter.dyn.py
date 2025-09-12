import logging
from functools import cached_property

from . import htypes
from .code.mark import mark
from .code.list_adapter import IndexListAdapterMixin, FnListAdapterBase

log = logging.getLogger(__name__)


class GitLogAdapter(FnListAdapterBase, IndexListAdapterMixin):

    @classmethod
    @mark.actor.ui_adapter_creg
    def from_piece(cls, piece, model, ctx,
                   system_fn_creg, client_feed_factory, column_visible_reg, peer_creg):
        fn = system_fn_creg.invite(piece.system_fn)
        _unused_remote_peer, real_model = cls._resolve_model(peer_creg, model)
        assert isinstance(real_model, htypes.git.log_model)
        return cls(system_fn_creg, client_feed_factory, column_visible_reg,
                   model, real_model, ctx, fn)

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
