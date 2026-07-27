from . import htypes
from .services import (
    pyobj_creg,
    web,
    )


class TypedDictConfig:

    @classmethod
    def from_config_piece(cls, piece):
        pass

    @classmethod
    def from_service_piece(cls, piece):
        assert 0, piece

    def __init__(self):
        pass

    def piece_list_to_config(self, piece_list):
        config = {}
        for piece in piece_list:
            assert isinstance(piece, htypes.system.typed_item_list), piece
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

    def piece_list_to_config(self, piece_list):
        config = {}
        for piece in piece_list:
            assert isinstance(piece, htypes.system.data_item_list)
            for item in piece.items:
                key = web.summon(item.key)
                value = web.summon(item.value)
                config[key] = value
        return config
