from . import htypes
from .services import (
    pyobj_creg,
    web,
    )


class TypedDictConfig:

    @classmethod
    def from_config_piece(cls, piece):
        pass

    def __init__(self):
        pass

    def from_piece_list(self, piece_list):
        config = {}
        for piece in piece_list:
            assert isinstance(piece, htypes.system.typed_item_list)
            for item in piece.items:
                t = pyobj_creg.invite(item.t)
                value = web.summon(item.value)
                config[t] = value
        return config


class DataDictConfig:

    @classmethod
    def from_config_piece(cls, piece):
        pass

    def __init__(self):
        pass

    def from_piece_list(self, piece_list):
        config = {}
        for piece in piece_list:
            assert isinstance(piece, htypes.system.data_item_list)
            for item in piece.items:
                key = web.summon(item.key)
                value = web.summon(item.value)
                config[key] = value
        return config
