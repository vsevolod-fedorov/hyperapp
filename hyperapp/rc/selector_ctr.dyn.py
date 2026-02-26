from functools import cached_property
from hyperapp.boot.htypes import TRecord

from . import htypes
from .services import (
    mosaic,
    pyobj_creg,
    )
from .code.rc_constructor import Constructor, ModuleCtr
from .code.cfg_item_req import CfgItemReq
from .code.ctx_actor_ctr import CtxActorTemplateCtr


_ACTION_SERVICE_NAME = 'selector_action'


def _action_resource_name(type_name, action):
    return f'{type_name}.selector.{action}'


class SelectorTemplateCtrBase(ModuleCtr):

    def __init__(self, module_name, attr_qual_name, service_params, value_t):
        super().__init__(module_name)
        self._attr_qual_name = attr_qual_name
        self._service_params = service_params
        self._value_t = value_t

    def update_resource_targets(self, resource_tgt, target_set):
        ready_tgt = target_set.factory.config_item_ready(_ACTION_SERVICE_NAME, self._resource_name)
        resolved_tgt = target_set.factory.config_item_resolved(_ACTION_SERVICE_NAME, self._resource_name)
        ready_tgt.set_provider(resource_tgt)
        resolved_tgt.resolve(self)
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
        return f'{self._value_t.module_name}_{self._value_t.name}_selector_{self._action_name}'

    @cached_property
    def _action_t(self):
        l = self._module_name.split('.')
        if l[-1] == 'tests':
            code_name = '_'.join(l[-2:])
        else:
            code_name = l[-1]
        return TRecord(code_name, self._action_full_name)

    @property
    def action(self):
        return self._action_t()

    @property
    def resource_name(self):
        return self._resource_name

    @property
    def _type_name(self):
        return f'{self._value_t.module_name}-{self._value_t.name}'

    @property
    def _resource_name(self):
        return _action_resource_name(self._type_name, self._action_name)


class SelectorOpenTemplateCtr(SelectorTemplateCtrBase):

    _action_name = 'open'
    _actor_creg = 'selector_open_action_creg'
    _ctx_params = ['value']

    @classmethod
    def from_piece(cls, piece):
        return cls(
            module_name=piece.module_name,
            attr_qual_name=piece.attr_qual_name,
            service_params=piece.service_params,
            value_t=pyobj_creg.invite(piece.value_t),
            model_t=pyobj_creg.invite(piece.model_t),
            )

    def __init__(self, module_name, attr_qual_name, service_params, value_t, model_t):
        super().__init__(module_name, attr_qual_name, service_params, value_t)
        self._model_t = model_t

    @property
    def piece(self):
        return htypes.selector_resources.open_ctr(
            module_name=self._module_name,
            attr_qual_name=tuple(self._attr_qual_name),
            service_params=tuple(self._service_params),
            value_t=pyobj_creg.actor_to_ref(self._value_t),
            model_t=pyobj_creg.actor_to_ref(self._model_t),
            )

    def update_resource_targets(self, resource_tgt, target_set):
        super().update_resource_targets(resource_tgt, target_set)
        self._add_selector_ctr(resource_tgt, target_set)

    def _add_selector_ctr(self, resource_tgt, target_set):
        ctr = SelectorCtr(self._value_t, self._model_t)
        ctr.update_selector_targets(resource_tgt, target_set)


class SelectorPickTemplateCtr(SelectorTemplateCtrBase):

    _action_name = 'pick'
    _actor_creg = 'selector_pick_action_creg'

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
        super().__init__(module_name, attr_qual_name, service_params, value_t)
        self._ctx_params = ctx_params

    @property
    def piece(self):
        return htypes.selector_resources.pick_ctr(
            module_name=self._module_name,
            attr_qual_name=tuple(self._attr_qual_name),
            ctx_params=tuple(self._ctx_params),
            service_params=tuple(self._service_params),
            value_t=pyobj_creg.actor_to_ref(self._value_t),
            )


class SelectorCtr(Constructor):

    def __init__(self, value_t, model_t):
        self._value_t = value_t
        self._model_t = model_t
        self._open_resolved_tgt = None
        self._pick_resolved_tgt = None

    def update_selector_targets(self, resource_tgt, target_set):
        self._open_resolved_tgt = target_set.factory.config_item_resolved(
            _ACTION_SERVICE_NAME, _action_resource_name(self._type_name, 'open'))
        self._pick_resolved_tgt = target_set.factory.config_item_resolved(
            _ACTION_SERVICE_NAME, _action_resource_name(self._type_name, 'pick'))
        service_name = 'selector_reg'
        req = CfgItemReq.from_actor(service_name, self._value_t)
        _, resolved_tgt, _ = target_set.factory.config_items(
            service_name, self._type_name, req, provider=resource_tgt, ctr=self)
        resolved_tgt.add_dep(self._open_resolved_tgt)
        resolved_tgt.add_dep(self._pick_resolved_tgt)
        resource_tgt.add_cfg_item_target(resolved_tgt)

    def get_component(self, name_to_res):
        return name_to_res[f'{self._type_name}.selector-cfg-item']

    def make_component(self, types, python_module, name_to_res):
        open_action = self._open_resolved_tgt.constructor.action
        open_action_res_name = self._open_resolved_tgt.constructor.resource_name
        pick_action = self._pick_resolved_tgt.constructor.action
        pick_action_res_name = self._pick_resolved_tgt.constructor.resource_name
        template = htypes.selector.template(
            model_t=pyobj_creg.actor_to_ref(self._model_t),
            open_action=mosaic.put(open_action),
            pick_action=mosaic.put(pick_action),
            )
        cfg_item = htypes.cfg_item.typed_cfg_item(
            t=pyobj_creg.actor_to_ref(self._value_t),
            value=mosaic.put(template),
            )
        name_to_res[f'{open_action_res_name}.action'] = open_action
        name_to_res[f'{pick_action_res_name}.action'] = pick_action
        name_to_res[f'{self._type_name}.selector-template'] = template
        name_to_res[f'{self._type_name}.selector-cfg-item'] = cfg_item

    @property
    def _type_name(self):
        return f'{self._value_t.module_name}-{self._value_t.name}'
