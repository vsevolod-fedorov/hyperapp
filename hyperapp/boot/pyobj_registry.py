import logging
from functools import partial

from .cached_code_registry import CachedCodeRegistry

log = logging.getLogger(__name__)


class PyObjRegistry(CachedCodeRegistry):

    def __init__(self, config, reconstructors):
        super().__init__(None, self, None, 'pyobj_creg', config)
        self._reconstructors = reconstructors

    def init(self, mosaic, web):
        self._mosaic = mosaic
        self._web = web

    def actor_to_piece(self, actor, reconstruct=True):
        try:
            return super().actor_to_piece(actor)
        except KeyError:
            if not reconstruct:
                raise
            for rctr in self._reconstructors:
                piece = rctr(actor)
                if piece is not None:
                    log.debug("Reconstructed actor %r to %r using %r", actor, piece, rctr)
                    self.add_to_cache(piece, actor)
                    return piece
            raise

    def register_actor(self, t, factory, **kw):
        self.update_resolved_config({t: partial(factory, **kw)})
