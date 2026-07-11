from ..htypes import (
    BUILTIN_MODULE_NAME,
    tString,
    TRecord,
    optional_mt,
    )
from ..dict_decoder import NamedPairsDictDecoder
from ..dict_encoder import NamedPairsDictEncoder


optional_def_mt = TRecord(BUILTIN_MODULE_NAME, 'optional_def_mt', {
    'base': tString,
    })


class OptionalMtResourceType:

    name = 'optional_mt'
    resource_t = optional_mt
    definition_t = optional_def_mt

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"<ResourceType: {self.name!r}>"

    def from_dict(self, data):
        decoder = NamedPairsDictDecoder()
        return decoder.decode_dict(data, self.definition_t)

    def to_dict(self, definition):
        encoder = NamedPairsDictEncoder()
        return encoder.encode_dict(definition)

    def resolve(self, definition, ctx):
        piece = optional_mt(
            base=ctx.resolve_to_ref(definition.base),
            )
        sources = {}
        return (piece, sources)

    def reverse_resolve(self, resource, resolver, resource_dir):
        return optional_def_mt(
            base=resolver(resource.base),
            )
