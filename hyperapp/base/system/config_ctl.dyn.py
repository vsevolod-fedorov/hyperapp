from abc import ABCMeta, abstractmethod

from hyperapp.boot.config_item_missing import ConfigItemMissingError

from . import htypes
from .services import (
    mosaic,
    web,
    )


class ConfigCtl(metaclass=ABCMeta):

    is_multi_item = False

    @abstractmethod
    def from_data(self, piece):
        pass

    @abstractmethod
    def to_data(self, config):
        pass

    @abstractmethod
    def empty_config_template(self):
        pass

    @abstractmethod
    def merge(self, dest, src):
        pass

    @abstractmethod
    def resolve(self, system, service_name, config_template):
        pass


class MultiItemConfigCtl(ConfigCtl, metaclass=ABCMeta):

    is_multi_item = True

    def __init__(self, cfg_item_creg=None):
        self._cfg_item_creg = cfg_item_creg

    def from_data(self, piece):
        config_template = self.empty_config_template()
        for item_ref in piece.items:
            item = self._cfg_item_creg.invite(item_ref)
            self._update_config(config_template, item)
        return config_template

    def to_data(self, config_template):
        item_pieces = self.config_to_item_pieces(config_template)
        return self._item_pieces_to_data(item_pieces)

    def config_to_item_pieces(self, config_template):
        return [
            self.item_piece(value)
            for value in self._config_to_items(config_template)
            ]

    @staticmethod
    def _config_to_items(config_template):
        return config_template.values()

    @abstractmethod
    def _update_config(self, config_template, item):
        pass

    def item_piece(self, item):
        return self._cfg_item_creg.actor_to_piece(item)

    def _item_pieces_to_data(self, item_list):
        return item_pieces_to_data(item_list)


class LazyDictConfig:

    def __init__(self, ctl, system, service_name, config_template):
        self._ctl = ctl
        self._system = system
        self._service_name = service_name
        self._config_template = config_template  # key -> template
        self._resolved_config = {}

    def __getitem__(self, key):
        return self._resolve_key(key)

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def items(self):
        return self._items.items()

    def values(self):
        return self._items.values()

    @property
    def _items(self):
        items = {**self._resolved_config}
        for key, value_template in self._config_template.items():
            if key in items:
                continue
            value = self._resolve_template(key, value_template)
            items[key] = value
        return items

    def setdefault(self, key, default):
        try:
            return self._resolve_key(key)
        except KeyError:
            self._resolved_config[key] = default
            return default

    def update(self, config):
        self._resolved_config.update(config)

    def _resolve_key(self, key):
        try:
            return self._resolved_config[key]
        except KeyError:
            pass
        value_template = self._config_template[key]  # KeyError is raised from here.
        return self._resolve_template(key, value_template)

    def _resolve_template(self, key, value_template):
        try:
            value = self._ctl.resolve_item(self._system, self._service_name, value_template)
        except ConfigItemMissingError:
            raise
        except KeyError as x:
            # This is not a key error for the caller.
            raise RuntimeError(
                f"Error resolving {self._service_name} config tempate for {key!r}: {x.__class__.__name__}: {x}") from x
        self._resolved_config[key] = value
        return value


class DictConfigCtl(MultiItemConfigCtl):

    @classmethod
    def from_piece(cls, piece, cfg_item_creg):
        return cls(cfg_item_creg)

    @property
    def piece(self):
        return htypes.system.dict_config_ctl()

    def merge(self, dest, src):
        dest.update(src)
        return dest

    def _lazy_config(self, system, service_name, config_template):
        return LazyDictConfig(self, system, service_name, config_template)

    def resolve(self, system, service_name, config_template):
        return self._lazy_config(system, service_name, config_template)

    def resolve_item(self, system, service_name, item):
        return item.resolve(system, service_name)

    def empty_config_template(self):
        return {}

    def _update_config(self, config_template, item):
        config_template[item.key] = item


class FlatListConfigCtl(MultiItemConfigCtl):

    @classmethod
    def from_piece(cls, piece, cfg_item_creg):
        return cls(cfg_item_creg)

    @property
    def piece(self):
        return htypes.system.flat_list_config_ctl()

    @staticmethod
    def _config_to_items(config_template):
        return config_template

    def empty_config_template(self):
        return []

    def _update_config(self, config_template, item):
        config_template.append(item)

    def merge(self, dest, src):
        dest.extend(src)
        return dest

    def resolve(self, system, service_name, config_template):
        config = []  # command list.
        for item in config_template:
            value = item.resolve(system, service_name)
            config.append(value)
        return config


def service_pieces_to_config(service_to_config_piece):
    return htypes.system.system_config(tuple(
        htypes.system.service_config(
            service=service_name,
            config=mosaic.put(piece),
            )
        for service_name, piece in service_to_config_piece.items()
        ))


def item_pieces_to_data(item_list):
    return htypes.system.item_list_config(
        items=tuple(
            mosaic.put(item)
            for item in item_list
            ),
        )


# Only MultiItemConfigCtl services are expected.
def merge_system_config_pieces(x, y):
    x_map = {
        rec.service: rec.config
        for rec in x.services
        }
    y_map = {
        rec.service: rec.config
        for rec in y.services
        }
    service_to_config_ref = {}
    for service_name in set([*x_map, *y_map]):
        x_config_ref = x_map.get(service_name)
        y_config_ref = y_map.get(service_name)
        if x_config_ref is not None and y_config_ref is not None:
            x_config = web.summon(x_config_ref)
            y_config = web.summon(y_config_ref)
            assert isinstance(x_config, htypes.system.item_list_config)
            assert isinstance(y_config, htypes.system.item_list_config)
            config = htypes.system.item_list_config(
                # Preserve sorting order. Duplicates are ok.
                items=tuple([*x_config.items, *y_config.items]),
                )
            config_ref = mosaic.put(config)
        elif x_config_ref is not None:
            config_ref = x_config_ref
        else:
            config_ref = y_config_ref
        service_to_config_ref[service_name] = config_ref
    return htypes.system.system_config(tuple(
        htypes.system.service_config(
            service=service_name,
            config=config_ref,
            )
        for service_name, config_ref in service_to_config_ref.items()
        ))
