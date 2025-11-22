from . import htypes
from .services import (
    mosaic,
    )
from .code.rc_constructor import ModuleCtr
from .code.config_item_resource import ConfigItemResource


class DataConfigCtr(ModuleCtr):

    def __init__(self, module_name, service_name, name, key, value):
        super().__init__(module_name)
        self._service_name = service_name
        self._name = name
        self._key = key
        self._value = value

    def update_resource_targets(self, resource_tgt, target_set):
        resource_tgt.import_tgt.add_test_ctr(self)
        ready_tgt = target_set.factory.config_item_ready(self._service_name, self._name)
        ready_tgt.set_provider(resource_tgt)
        resolved_tgt = target_set.factory.config_item_resolved(self._service_name, self._name)
        resource_tgt.add_cfg_item_target(resolved_tgt)

    def make_component(self, types, python_module, name_to_res=None):
        return htypes.cfg_item.data_cfg_item(
            key=mosaic.put(self._key),
            value=mosaic.put(self._value),
            )

    def make_resource(self, types, module_name, python_module):
        item = self.make_component(types, python_module)
        return ConfigItemResource(
            service_name=self._service_name,
            cfg_item_ref=mosaic.put(item),
            )
