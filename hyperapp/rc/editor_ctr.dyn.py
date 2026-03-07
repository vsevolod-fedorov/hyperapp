from functools import cached_property
from hyperapp.boot.htypes import TRecord

from . import htypes
from .services import (
    mosaic,
    pyobj_creg,
    )
from .code.rc_constructor import ModuleCtr
from .code.ctx_actor_ctr import CtxActorTemplateCtr


class EditorDefaultTemplateCtr(ModuleCtr):

    _service_name = 'editor_default_reg'
    _actor_creg = 'crud_init_action_creg'

    @classmethod
    def from_piece(cls, piece):
        return cls(
            module_name=piece.module_name,
            attr_qual_name=piece.attr_qual_name,
            ctx_params=piece.ctx_params,
            service_params=piece.service_params,
            value_t=pyobj_creg.invite(piece.value_t),
            )

    def __init__(self, module_name, attr_qual_name, ctx_params, service_params, value_t):
        super().__init__(module_name)
        self._attr_qual_name = attr_qual_name
        self._ctx_params = ctx_params
        self._service_params = service_params
        self._value_t = value_t

    @property
    def piece(self):
        return htypes.editor_ctr.default_ctr(
            module_name=self._module_name,
            attr_qual_name=tuple(self._attr_qual_name),
            ctx_params=tuple(self._ctx_params),
            service_params=tuple(self._service_params),
            value_t=pyobj_creg.actor_to_ref(self._value_t),
            )

    def update_resource_targets(self, resource_tgt, target_set):
        ready_tgt, resolved_tgt, _ = target_set.factory.config_items(
            self._service_name, self._resource_name,
            provider=resource_tgt,
            ctr=self,
            )
        resource_tgt.add_cfg_item_target(resolved_tgt)
        actor_ctr = CtxActorTemplateCtr(
            module_name=self._module_name,
            attr_qual_name=self._attr_qual_name,
            service_name=self._actor_creg,
            t=self._action_t,
            ctx_params=self._ctx_params,
            service_params=self._service_params,
            create_t=True,
            )
        actor_ctr.update_resource_targets(resource_tgt, target_set)

    @property
    def _action_full_name(self):
        return f'{self._value_t.module_name}_{self._value_t.name}_editor_default'

    @cached_property
    def _action_t(self):
        code_name = self._module_name.split('.')[-1]
        return TRecord(code_name, self._action_full_name)

    def get_component(self, name_to_res):
        return name_to_res[f'{self._resource_name}.cfg-item']

    def make_component(self, types, python_module, name_to_res):
        action = self._action_t()
        cfg_item = htypes.cfg_item.typed_cfg_item(
            t=pyobj_creg.actor_to_ref(self._value_t),
            value=mosaic.put(action),
            )
        name_to_res[f'{self._type_name}.action'] = action
        name_to_res[f'{self._resource_name}.cfg-item'] = cfg_item
        return cfg_item

    @property
    def _type_name(self):
        return f'{self._value_t.module_name}-{self._value_t.name}'

    @property
    def _resource_name(self):
        return f'{self._type_name}.editor_default'
