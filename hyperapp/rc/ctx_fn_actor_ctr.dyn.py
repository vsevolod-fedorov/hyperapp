from . import htypes
from .services import (
    mosaic,
    pyobj_creg,
    )
from .code.rc_constructor import ModuleCtr
from .code.cfg_item_req import CfgItemReq


class CtxFnActorTemplateCtr(ModuleCtr):

    def __init__(self, module_name, attr_qual_name, service_name, t, ctx_params, service_params, create_t=False):
        super().__init__(module_name)
        self._service_name = service_name
        self._t = t
        self._attr_qual_name = attr_qual_name
        self._ctx_params = ctx_params
        self._service_params = service_params
        self._create_t = create_t

    def update_resource_targets(self, resource_tgt, target_set):
        req = CfgItemReq.from_actor(self._service_name, self._t)
        _, resolved_tgt, _ = target_set.factory.config_items(
            self._service_name, self._type_name, req,
            provider=resource_tgt,
            ctr=self,
            )
        resource_tgt.add_cfg_item_target(resolved_tgt)

    def get_component(self, name_to_res):
        return name_to_res[self._resource_name]

    def make_component(self, types, python_module, name_to_res=None):
        object = python_module
        prefix = []
        for name in self._attr_qual_name:
            object = htypes.builtin.attribute(
                object=mosaic.put(object),
                attr_name=name,
                )
            if name_to_res is not None:
                attr_name = '.'.join([*prefix, name])
                name_to_res[attr_name] = object
            prefix.append(name)
        system_fn = htypes.system_fn.ctx_fn(
            function=mosaic.put(object),
            ctx_params=tuple(self._ctx_params),
            service_params=tuple(self._service_params),
            )
        template = htypes.cfg_item.fn_value_template(
            system_fn=mosaic.put(system_fn),
            )
        cfg_item = htypes.cfg_item.typed_cfg_item(
            t=pyobj_creg.actor_to_ref(self._t),
            value=mosaic.put(template),
            )
        if name_to_res is not None:
            if self._create_t:
                t_piece = pyobj_creg.actor_to_piece(self._t)
                name_to_res[f'{t_piece.name}.t'] = t_piece
            name_to_res[f'{attr_name}.system-fn'] = system_fn
            name_to_res[f'{attr_name}.ctx-actor-template'] = template
            name_to_res[self._resource_name] = cfg_item
        return cfg_item

    @property
    def _type_name(self):
        return f'{self._t.module_name}-{self._t.name}'

    @property
    def _resource_name(self):
        return f'{self._service_name}-{self._type_name}.ctx-actor-cfg-item'
