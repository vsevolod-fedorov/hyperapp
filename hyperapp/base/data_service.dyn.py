from . import htypes
from .services import (
    web,
    )
from .code.config_key_ctl import DataKeyCtl, TypeKeyCtl
from .code.config_ctl import DataValueCtl, DictConfigCtl, LazyDictConfig, item_pieces_to_data


class DataServiceConfigCtl(DictConfigCtl):

    @classmethod
    def from_piece(cls, piece):
        return cls()

    def __init__(self):
        super().__init__(
            key_ctl=DataKeyCtl(),
            value_ctl=DataValueCtl(),
            )

    @property
    def piece(self):
        return htypes.data_service.config_ctl()


class TypeKeyDataServiceConfigCtl(DictConfigCtl):

    @classmethod
    def from_piece(cls, piece):
        return cls()

    @property
    def piece(self):
        return htypes.data_service.type_key_config_ctl()

    def __init__(self):
        super().__init__(
            key_ctl=TypeKeyCtl(),
            value_ctl=DataValueCtl(),
            )


def config_item_name(piece, gen):
    key = web.summon(piece.key)
    key_name = gen.assigned_name(key)
    suffix = key_name.replace(':', '-')
    return f'config_item-{suffix}'
