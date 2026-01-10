from . import htypes
from .services import (
    mosaic,
    pyobj_creg,
    )
from .code.rc_constructor import ModuleCtr
from .code.config_item_resource import ConfigItemResource
from .code.cfg_item_req import CfgItemReq


class CtxActorProbeCtr(ModuleCtr):

    @classmethod
    def from_piece(cls, piece):
        return cls(
            module_name=piece.module_name,
            attr_qual_name=piece.attr_qual_name,
            service_name=piece.service_name,
            t=pyobj_creg.invite(piece.t),
            has_params=piece.has_params,
            )

    def __init__(self, module_name, attr_qual_name, service_name, t, has_params):
        super().__init__(module_name)
        self._attr_qual_name = attr_qual_name
        self._service_name = service_name
        self._t = t
        self._has_params = has_params

    @property
    def piece(self):
        return htypes.actor_resource.ctx_actor_probe_ctr(
            module_name=self._module_name,
            attr_qual_name=tuple(self._attr_qual_name),
            service_name=self._service_name,
            t=pyobj_creg.actor_to_ref(self._t),
            has_params=self._has_params,
            )

    def update_fixtures_targets(self, import_tgt, target_set):
        if not self._has_params:
            import_tgt.add_test_ctr(self)
        # else:
        #     assert 0, (self._module_name, import_tgt)

    def update_resource_targets(self, resource_tgt, target_set):
        resource_tgt.import_tgt.add_test_ctr(self)
        ready_tgt = target_set.factory.config_item_ready(self._service_name, self._type_name)
        ready_tgt.set_provider(resource_tgt)
        resolved_tgt = target_set.factory.config_item_resolved(self._service_name, self._type_name)
        resource_tgt.add_cfg_item_target(resolved_tgt)

    def make_component(self, types, python_module, name_to_res=None):
        object = python_module
        for name in self._attr_qual_name:
            object = htypes.builtin.attribute(
                object=mosaic.put(object),
                attr_name=name,
                )
        template = htypes.actor_resource.ctx_actor_probe_template(
            function=mosaic.put(object),
            )
        return htypes.cfg_item.typed_cfg_item(
            t=pyobj_creg.actor_to_ref(self._t),
            value=mosaic.put(template),
            )

    def make_resource(self, types, module_name, python_module):
        item = self.make_component(types, python_module)
        return ConfigItemResource(
            service_name=self._service_name,
            cfg_item_ref=mosaic.put(item),
            )

    @property
    def _type_name(self):
        return f'{self._t.module_name}-{self._t.name}'


class CtxFnCtr:

    _value_template_suffix = 'ctx-actor-template'

    def __init__(self, attr_qual_name, ctx_params, service_params):
        self._attr_qual_name = attr_qual_name
        self._ctx_params = ctx_params
        self._service_params = service_params

    def make_value_template(self, python_module, name_to_res=None):
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
        if name_to_res is not None:
            name_to_res[f'{attr_name}.system-fn'] = system_fn
            name_to_res[f'{attr_name}.{self._value_template_suffix}'] = template
        return template


class CtxActorTemplateCtr(ModuleCtr, CtxFnCtr):

    @classmethod
    def from_piece(cls, piece):
        return cls(
            module_name=piece.module_name,
            attr_qual_name=piece.attr_qual_name,
            service_name=piece.service_name,
            t=pyobj_creg.invite(piece.t),
            ctx_params=piece.ctx_params,
            service_params=piece.service_params,
            )

    def __init__(self, module_name, attr_qual_name, service_name, t, ctx_params, service_params, create_t=False):
        super().__init__(module_name)
        CtxFnCtr.__init__(self, attr_qual_name, ctx_params, service_params)
        self._service_name = service_name
        self._t = t
        self._create_t = create_t

    @property
    def piece(self):
        return htypes.actor_resource.ctx_actor_template_ctr(
            module_name=self._module_name,
            attr_qual_name=tuple(self._attr_qual_name),
            service_name=self._service_name,
            t=pyobj_creg.actor_to_ref(self._t),
            ctx_params=tuple(self._ctx_params),
            service_params=tuple(self._service_params),
            )

    def update_fixtures_targets(self, import_tgt, target_set):
        if import_tgt.module_name != self._module_name:
            return   # Only for constructors created from tests themselves.
        import_tgt.add_test_ctr(self)
        # assert 0, (self._service_name, self._attr_qual_name, self._t, import_tgt)

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
        template = self.make_value_template(python_module, name_to_res)
        cfg_item = htypes.cfg_item.typed_cfg_item(
            t=pyobj_creg.actor_to_ref(self._t),
            value=mosaic.put(template),
            )
        if name_to_res is not None:
            if self._create_t:
                t_piece = pyobj_creg.actor_to_piece(self._t)
                name_to_res[f'{t_piece.name}.t'] = t_piece
            name_to_res[self._resource_name] = cfg_item
        return cfg_item

    def make_resource(self, types, module_name, python_module):
        item = self.make_component(types, python_module)
        return ConfigItemResource(
            service_name=self._service_name,
            cfg_item_ref=mosaic.put(item),
            )

    @property
    def _type_name(self):
        return f'{self._t.module_name}-{self._t.name}'

    @property
    def _resource_name(self):
        return f'{self._service_name}-{self._type_name}.ctx-actor-cfg-item'
