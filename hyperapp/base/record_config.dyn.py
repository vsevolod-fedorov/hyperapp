from . import htypes
from .code.config_ctl import ConfigCtl


class RecordConfigCtl(ConfigCtl):

    @classmethod
    def from_piece(cls, piece):
        return cls()

    @property
    def piece(self):
        return htypes.record_config.config_ctl()

    def from_data(self, piece):
        return piece

    def to_data(self, config):
        return config

    def empty_config_template(self):
        return None

    def merge(self, dest, src):
        return src

    def resolve(self, system, service_name, config_template):
        return config_template
