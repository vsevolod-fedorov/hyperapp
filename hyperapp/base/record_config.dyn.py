from . import htypes
from .services import (
    pyobj_creg,
    )
from .code.config_ctl import ConfigCtl


class RecordConfigCtl(ConfigCtl):

    @classmethod
    def from_piece(cls, piece):
        t = pyobj_creg.invite(piece.t)
        return cls(t)

    def __init__(self, t):
        self._t = t

    @property
    def piece(self):
        return htypes.record_config.config_ctl(
            t=pyobj_creg.actor_to_ref(self._t),
            )

    def from_data(self, piece):
        return piece

    def to_data(self, config):
        return config

    def empty_config_template(self):
        return self._t.make_default_value()

    def merge_config(self, dest, src):
        return src

    def merge_template(self, dest, src):
        return src

    def resolve(self, system, service_name, config_template):
        return config_template
