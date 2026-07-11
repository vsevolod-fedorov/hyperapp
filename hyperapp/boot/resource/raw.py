from ..htypes.raw import raw_t, raw_def_t
from ..dict_decoder import NamedPairsDictDecoder
from ..dict_encoder import NamedPairsDictEncoder


class RawResourceType:

    resource_t = raw_t
    definition_t = raw_def_t

    def __str__(self):
        return 'raw'

    def __repr__(self):
        return "<ResourceType: 'raw'>"

    def from_dict(self, data):
        decoder = NamedPairsDictDecoder()
        return decoder.decode_dict(data, self.definition_t)

    def to_dict(self, definition):
        encoder = NamedPairsDictEncoder()
        return encoder.encode_dict(definition)

    def resolve(self, definition, ctx):
        return raw_t(
            resource=ctx.resolve_to_ref(definition.resource),
            )

    def reverse_resolve(self, resource, resolver, resource_dir):
        return raw_def_t(
            resource=resolver(resource.resource),
            )


def raw_pyobj(piece, web):
    return web.summon(piece.resource)
