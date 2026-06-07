from ..htypes import (
    BUILTIN_MODULE_NAME,
    tString,
    TList,
    TOptional,
    TRecord,
    field_mt,
    record_mt,
    )
from ..dict_decoder import NamedPairsDictDecoder
from ..dict_encoder import NamedPairsDictEncoder


field_def_mt = TRecord(BUILTIN_MODULE_NAME, 'field_def_mt', {
    'name': tString,
    'type': tString,
    })

record_def_mt = TRecord(BUILTIN_MODULE_NAME, 'record_def_mt', {
    'name': tString,
    'base': TOptional(tString),
    'fields': TList(field_def_mt),
    })


class RecordMtResourceType:

    name = 'record_mt'
    resource_t = record_mt
    definition_t = record_def_mt

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"<ResourceType: {self.name!r}>"

    def from_dict(self, data):
        decoder = NamedPairsDictDecoder()
        return decoder.decode_dict(self.definition_t, data)

    def to_dict(self, definition):
        encoder = NamedPairsDictEncoder()
        return encoder.encode(definition)

    def resolve(self, definition, ctx):
        piece = record_mt(
            module_name=ctx.path[-1],
            name=definition.name,
            base=ctx.resolve_to_ref_opt(definition.base),
            fields=tuple(
                field_mt(
                    name=field.name,
                    type=ctx.resolve_to_ref(field.type),
                    )
                for field in definition.fields
                ),
            )
        sources = {}
        return (piece, sources)

    def reverse_resolve(self, resource, resolver, resource_dir):
        raise NotImplementedError("TODO")
