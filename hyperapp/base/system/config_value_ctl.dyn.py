from functools import partial

from . import htypes


class ActorValueCtl:

    @classmethod
    def from_piece(cls, piece, cfg_value_creg):
        return cls(cfg_value_creg)

    def __init__(self, cfg_value_creg=None):
        self._cfg_value_creg = cfg_value_creg

    # def init(self, cfg_value_creg):
    #     self._cfg_value_creg = cfg_value_creg

    @property
    def piece(self):
        return htypes.system.actor_value_ctl()

    def resolve(self, template, key, system, service_name):
        return self._cfg_value_creg.animate(template, key, system, service_name)

    def reverse(self, value):
        return value.piece


class DataValueCtl:

    @classmethod
    def from_piece(cls, piece):
        return cls()

    # def init(self, cfg_value_creg):
    #     pass

    @property
    def piece(self):
        return htypes.system.data_value_ctl()

    def resolve(self, template, key, system, service_name):
        return template

    def reverse(self, value):
        return value


def config_value_ctl_creg_config(cfg_value_creg):
    return {
        htypes.system.actor_value_ctl: partial(ActorValueCtl.from_piece, cfg_value_creg=cfg_value_creg),
        htypes.system.data_value_ctl: DataValueCtl.from_piece,
        }
