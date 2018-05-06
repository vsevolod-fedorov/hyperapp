import logging

from ..common.interface import hyper_ref as href_types
from ..common.htypes import Type
from ..common.packet_coders import packet_coders
from .registry import Registry

log = logging.getLogger(__name__)



class PieceRegistry(Registry):

    def __init__(self, produce_name, type_registry_registry):
        super().__init__()
        self._produce_name = produce_name
        self._type_registry_registry = type_registry_registry

    @property
    def produce_name(self):
        return self._produce_name

    def register(self, t, factory, *args, **kw):
        assert isinstance(t, Type), repr(t)
        assert t.full_name, repr(t)  # type must have a name
        super().register(tuple(t.full_name), factory, *args, **kw)
        
    async def resolve(self, piece):
        assert isinstance(piece, href_types.piece), repr(piece)
        t = self._type_registry_registry.resolve_type(piece.full_type_name)
        object = packet_coders.decode(piece.encoding, piece.encoded_object, t)
        rec = self._resolve(tuple(piece.full_type_name))
        log.info('producing %s for %s using %s(%s, %s) for object %r',
                     self._produce_name, '.'.join(piece.full_type_name), rec.factory, rec.args, rec.kw, object)
        return (await self._run_awaitable_factory(rec.factory, object, *rec.args, **rec.kw))


class PieceResolver(object):

    def __init__(self, async_ref_resolver, piece_registry):
        self._async_ref_resolver = async_ref_resolver
        self._piece_registry = piece_registry

    async def resolve(self, ref):
        assert isinstance(ref, bytes), repr(ref)
        piece = await self._async_ref_resolver.resolve_ref(ref)
        produce = await self._piece_registry.resolve(piece)
        assert produce, repr(produce)
        log.debug('piece resolved to %s %r', self._piece_registry.produce_name, produce)
        return produce