from . import htypes
from .services import (
    mosaic,
    pyobj_creg,
    web,
    )


class StrKeyCtl:

    @classmethod
    def from_piece(cls, piece):
        return cls()

    @property
    def piece(self):
        return htypes.config_ctl.str_key_ctl()

    def split(self, piece):
        value = web.summon(piece.value)
        return (piece.key, value)

    def compose(self, key, value):
        return htypes.cfg_item.data_cfg_item(
            key=key,
            value=mosaic.put(value),
            )


class DataKeyCtl:

    @classmethod
    def from_piece(cls, piece):
        return cls()

    @property
    def piece(self):
        return htypes.config_ctl.data_key_ctl()

    def split(self, piece):
        key = web.summon(piece.key)
        value = web.summon(piece.value)
        return (key, value)

    def compose(self, key, value):
        return htypes.cfg_item.data_cfg_item(
            key=mosaic.put(key),
            value=mosaic.put(value),
            )


class TypeKeyCtl:

    @classmethod
    def from_piece(cls, piece):
        return cls()

    @property
    def piece(self):
        return htypes.config_ctl.type_key_ctl()

    def split(self, piece):
        key = pyobj_creg.invite(piece.t)
        value = web.summon(piece.value)
        return (key, value)

    def compose(self, key, value):
        return htypes.cfg_item.type_cfg_item(
            t=pyobj_creg.actor_to_ref(key),
            value=mosaic.put(value),
            )


def data_cfg_item_name(piece, gen):
    key = web.summon(piece.key)
    key_name = gen.assigned_name(key)
    suffix = key_name.replace(':', '-')
    return f'config_item-{suffix}'


def config_item_creg_config():
    return {
        htypes.config_ctl.str_key_ctl: StrKeyCtl.from_piece,
        htypes.config_ctl.data_key_ctl: DataKeyCtl.from_piece,
        htypes.config_ctl.type_key_ctl: TypeKeyCtl.from_piece,
        }
