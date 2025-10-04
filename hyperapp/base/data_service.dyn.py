from . import htypes
from .services import (
    mosaic,
    pyobj_creg,
    web,
    )
from .code.config_ctl import ConfigCtl, LazyDictConfig, item_pieces_to_data


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
            key, value = self.data_to_item(item)
            self._update_config(config_template, key, value)
        return config_template

    def to_data(self, config_template):
        return item_pieces_to_data([
            self.item_to_data(key, value)
            for key, value in config_template.items()
            ])

    def empty_config_template(self):
        return {}

    def merge(self, dest, src):
        dest.update(src)
        return dest

    def merge_template(self, dest, src):
        dest.update(src)
        return dest

    def resolve(self, system, service_name, config_template):
        return LazyDictConfig(self, system, service_name, system.default_layer, config_template)

    def config_to_items(self, config_template):
        return config_template.items()

    @staticmethod
    def data_to_item(piece):
        key = web.summon(piece.key)
        value = web.summon(piece.value)
        return (key, value)

    @staticmethod
    def item_to_data(key, value):
        return htypes.data_service.config_item(
            key=mosaic.put(key),
            value=mosaic.put(value),
            )

    def resolve_value(self, system, service_name, key, template):
        return template

    @staticmethod
    def _update_config(config_template, key, value):
        config_template[key] = value


class TypeKeyDataServiceConfigCtl(DataServiceConfigCtl):

    @classmethod
    def from_piece(cls, piece):
        return cls()

    @property
    def piece(self):
        return htypes.data_service.type_key_config_ctl()

    @staticmethod
    def data_to_item(piece):
        key = pyobj_creg.invite(piece.key)
        value = web.summon(piece.value)
        return (key, value)

    @staticmethod
    def item_to_data(key, value):
        return htypes.data_service.config_item(
            key=pyobj_creg.actor_to_ref(key),
            value=mosaic.put(value),
            )


def config_item_name(piece, gen):
    key = web.summon(piece.key)
    key_name = gen.assigned_name(key)
    suffix = key_name.replace(':', '-')
    return f'config_item-{suffix}'
