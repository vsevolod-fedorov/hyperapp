from . import htypes
from .services import (
    mosaic,
    )
from .code.rc_constructor import ModuleCtr
from .code.config_item_resource import ConfigItemResource


class DataConfigCtr(ModuleCtr):

    def __init__(
            self,
            module_name,
            service_name,
            name,
            key_resource_suffix,
            value_resource_suffix,
            item_resource_suffix,
            key,
            value,
            ):
        super().__init__(module_name)
        self._service_name = service_name
        self._name = name
        self._key_resource_suffix = key_resource_suffix
        self._value_resource_suffix = value_resource_suffix
        self._item_resource_suffix = item_resource_suffix
        self._key = key
        self._value = value

    def update_resource_targets(self, resource_tgt, target_set):
        resource_tgt.import_tgt.add_test_ctr(self)
        _, resolved_tgt, _ = target_set.factory.config_items(
            self._service_name, self._name,
            provider=resource_tgt,
            ctr=self,
            )
        resource_tgt.add_cfg_item_target(resolved_tgt)

    def get_component(self, name_to_res):
        return name_to_res[f'{self._name}.{self._item_resource_suffix}']

    def make_component(self, types, python_module, name_to_res=None):
        cfg_item = htypes.cfg_item.data_cfg_item(
            key=mosaic.put(self._key),
            value=mosaic.put(self._value),
            )
        if name_to_res is not None:
            name_to_res[f'{self._name}.{self._key_resource_suffix}'] = self._key
            name_to_res[f'{self._name}.{self._value_resource_suffix}'] = self._value
            name_to_res[f'{self._name}.{self._item_resource_suffix}'] = cfg_item
        return cfg_item

    def make_resource(self, types, module_name, python_module):
        item = self.make_component(types, python_module)
        return ConfigItemResource(
            service_name=self._service_name,
            cfg_item_ref=mosaic.put(item),
            )
