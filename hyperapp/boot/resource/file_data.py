import logging

from ..htypes.file_data import (
    file_data_t,
    file_data_def_t,
    )
from ..dict_decoder import NamedPairsDictDecoder
from ..dict_encoder import NamedPairsDictEncoder


log = logging.getLogger(__name__)


class FileDataType:

    name = 'file'
    resource_t = file_data_t
    definition_t = file_data_def_t

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
        data, project_name, path, sources = ctx.get_bytes(definition.file_name)
        piece = self.resource_t(
            data=data,
            )
        return (piece, sources)

    def reverse_resolve(self, resource, resolver, resource_dir):
        assert 0, "TODO"
