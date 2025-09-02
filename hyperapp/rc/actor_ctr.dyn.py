from . import htypes
from .services import (
    mosaic,
    pyobj_creg,
    )
from .code.rc_constructor import Constructor
from .code.config_item_resource import ConfigItemResource
from .code.cfg_item_req import CfgItemReq


class ActorProbeCtr(Constructor):

    @classmethod
    def from_piece(cls, piece):
        return cls(
            attr_qual_name=piece.attr_qual_name,
            service_name=piece.service_name,
            t=pyobj_creg.invite(piece.t),
            )

    def __init__(self, attr_qual_name, service_name, t):
        self._attr_qual_name = attr_qual_name
        self._service_name = service_name
        self._t = t

    @property
    def piece(self):
        return htypes.actor_resource.actor_probe_ctr(
            attr_qual_name=tuple(self._attr_qual_name),
            service_name=self._service_name,
            t=pyobj_creg.actor_to_ref(self._t),
            )

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
        template = htypes.actor_resource.actor_probe_template(
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


class ActorTemplateCtrBase(Constructor):

    def __init__(self, service_name, t):
        self._service_name = service_name
        self._t = t

    def get_component(self, name_to_res):
        return name_to_res[f'{self._resource_name}.actor-cfg-item']

    @property
    def _type_name(self):
        return f'{self._t.module_name}-{self._t.name}'

    @property
    def _resource_name(self):
        return f'{self._service_name}-{self._type_name}'


class CoreActorTemplateCtr(ActorTemplateCtrBase):

    @classmethod
    def from_cfg_item_piece(cls, piece, service_name, var_name):
        return cls(
            service_name=service_name,
            t=pyobj_creg.invite(piece.t),
            )


class ActorTemplateCtr(ActorTemplateCtrBase):

    @classmethod
    def from_piece(cls, piece):
        return cls(
            module_name=piece.module_name,
            attr_qual_name=piece.attr_qual_name,
            service_name=piece.service_name,
            t=pyobj_creg.invite(piece.t),
            creg_params=piece.creg_params,
            service_params=piece.service_params,
            )

    def __init__(self, module_name, attr_qual_name, service_name, t, creg_params, service_params):
        super().__init__(service_name, t)
        self._module_name = module_name
        self._attr_qual_name = attr_qual_name
        self._creg_params = creg_params
        self._service_params = service_params

    @property
    def piece(self):
        return htypes.actor_resource.actor_template_ctr(
            module_name=self._module_name,
            attr_qual_name=tuple(self._attr_qual_name),
            service_name=self._service_name,
            t=pyobj_creg.actor_to_ref(self._t),
            creg_params=tuple(self._creg_params),
            service_params=tuple(self._service_params),
            )

    def update_targets(self, target_set):
        resource_tgt = target_set.factory.python_module_resource_by_module_name(self._module_name)
        # Ready target may already have provider set, but when marker is non-typed it have not.
        req = CfgItemReq.from_actor(self._service_name, self._t)
        ready_tgt, resolved_tgt, _ = target_set.factory.config_items(
            self._service_name, self._type_name, req,
            provider=resource_tgt,
            ctr=self,
            )
        # Resource target may already have resolved target, but when marker is non-typed it have not.
        resource_tgt.add_cfg_item_target(resolved_tgt)

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
        template = htypes.system.actor_template(
            function=mosaic.put(object),
            service_params=tuple(self._service_params),
            )
        cfg_item = htypes.cfg_item.typed_cfg_item(
            t=pyobj_creg.actor_to_ref(self._t),
            value=mosaic.put(template),
            )
        if name_to_res is not None:
            name_to_res[f'{attr_name}.actor-template'] = template
            name_to_res[f'{self._resource_name}.actor-cfg-item'] = cfg_item
        return cfg_item
