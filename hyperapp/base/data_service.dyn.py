from . import htypes
from .services import (
    mosaic,
    pyobj_creg,
    web,
    )
from .code.config_ctl import ConfigCtl, item_pieces_to_data


class DataServiceConfigCtl(ConfigCtl):

    is_multi_item = True

    @classmethod
    def from_piece(cls, piece):
        return cls()

    @property
    def piece(self):
        return htypes.data_service.config_ctl()

    def from_data(self, piece):
        config_template = self.empty_config_template()
        for item_ref in piece.items:
            item = web.summon(item_ref)
            key, value = self._item_to_kv(item)
            self._update_config(config_template, key, value)
        return config_template

    def to_data(self, config_template):
        return item_pieces_to_data([
            self._item_piece(key, value)
            for key, value in config_template.items()
            ])

    def empty_config_template(self):
        return {}

    def merge(self, dest, src):
        dest.update(src)
        return dest

    def resolve(self, system, service_name, config_template):
        return DataServiceConfig(system, system.default_layer, service_name)

    def config_to_items(self, config_template):
        return config_template.items()

    @staticmethod
    def _item_to_kv(item):
        key = web.summon(item.key)
        value = web.summon(item.value)
        return (key, value)

    @staticmethod
    def _update_config(config_template, key, value):
        config_template[key] = value

    @staticmethod
    def _item_piece(key, value):
        return htypes.data_service.config_item(
            key=mosaic.put(key),
            value=mosaic.put(value),
            )


class TypeKeyDataServiceConfigCtl(DataServiceConfigCtl):

    @classmethod
    def from_piece(cls, piece):
        return cls()

    @property
    def piece(self):
        return htypes.data_service.type_key_config_ctl()

    @staticmethod
    def _item_to_kv(item):
        key = pyobj_creg.invite(item.key)
        value = web.summon(item.value)
        return (key, value)

    @staticmethod
    def _item_piece(key, value):
        return htypes.data_service.config_item(
            key=pyobj_creg.actor_to_ref(key),
            value=mosaic.put(value),
            )


class DataServiceConfig:

    def __init__(self, system, target_layer, service_name):
        self._system = system
        self._target_layer = target_layer
        self._service_name = service_name

    def get(self, key, default=None):
        config = self._system.get_config_template(self._service_name)
        return config.get(key, default)

    def __contains__(self, key):
        config = self._system.get_config_template(self._service_name)
        return key in config

    def __getitem__(self, key):
        config = self._system.get_config_template(self._service_name)
        return config[key]

    def __setitem__(self, key, value):
        self._target_layer.set(self._service_name, key, value)

    def __delitem__(self, key):
        self._target_layer.remove(self._service_name, key)

    # Used with config fixtures.
    def update(self, config):
        self._system.update_service_config(self._service_name, config)


def config_item_name(piece, gen):
    key = web.summon(piece.key)
    key_name = gen.assigned_name(key)
    suffix = key_name.replace(':', '-')
    return f'config_item-{suffix}'
