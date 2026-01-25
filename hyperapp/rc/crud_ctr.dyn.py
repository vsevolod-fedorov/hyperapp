from functools import cached_property
from hyperapp.boot.htypes import TRecord

from . import htypes
from .services import (
    mosaic,
    pyobj_creg,
    )
from .code.rc_constructor import ModuleCtr
from .code.ctx_actor_ctr import CtxActorTemplateCtr


class CrudTemplateCtr(ModuleCtr):

    _service_name = 'crud_action'

    def __init__(self, module_name, attr_qual_name, model_t, action_name, key_fields, ctx_params, service_params):
        super().__init__(module_name)
        self._attr_qual_name = attr_qual_name
        self._model_t = model_t
        self._action_name = action_name
        self._key_fields = key_fields
        self._ctx_params = ctx_params
        self._service_params = service_params

    def update_resource_targets(self, resource_tgt, target_set):
        ready_tgt = target_set.factory.config_item_ready(self._service_name, self._resource_name)
        resolved_tgt = target_set.factory.config_item_resolved(self._service_name, self._resource_name)
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
    def key_fields(self):
        return set(self._key_fields)

    @property
    def _action_full_name(self):
        return f'{self._type}_{self._action_name}'

    @cached_property
    def _action_t(self):
        code_name = self._module_name.split('.')[-1]
        return TRecord(code_name, self._action_full_name)

    def _make_resource_name(self, type, action_name):
        return f'{self._type_name}.crud.{type}.{action_name}'

    @property
    def _type_name(self):
        return f'{self._model_t.module_name}-{self._model_t.name}'

    @property
    def _resource_name(self):
        return self._make_resource_name(self._type, self._action_name)


class CrudInitTemplateCtr(CrudTemplateCtr):

    _type = 'init'
    _actor_creg = 'crud_init_action_creg'

    @classmethod
    def from_piece(cls, piece):
        return cls(
            module_name=piece.module_name,
            attr_qual_name=piece.attr_qual_name,
            model_t=pyobj_creg.invite(piece.model_t),
            action_name=piece.action_name,
            key_fields=piece.key_fields,
            ctx_params=piece.ctx_params,
            service_params=piece.service_params,
            value_t=pyobj_creg.invite(piece.value_t),
            )

    def __init__(self, module_name, attr_qual_name, model_t, action_name, key_fields, ctx_params, service_params, value_t):
        super().__init__(module_name, attr_qual_name, model_t, action_name, key_fields, ctx_params, service_params)
        self._value_t = value_t

    @property
    def piece(self):
        return htypes.crud_ctr.init_ctr(
            module_name=self._module_name,
            attr_qual_name=tuple(self._attr_qual_name),
            model_t=pyobj_creg.actor_to_ref(self._model_t),
            action_name=self._action_name,
            key_fields=tuple(self._key_fields),
            ctx_params=tuple(self._ctx_params),
            service_params=tuple(self._service_params),
            value_t=pyobj_creg.actor_to_ref(self._value_t),
            )

    @property
    def value_t(self):
        return self._value_t


class CrudCommitTemplateCtr(CrudTemplateCtr):

    _type = 'commit'
    _actor_creg = 'crud_commit_action_creg'

    @classmethod
    def from_piece(cls, piece):
        return cls(
            module_name=piece.module_name,
            attr_qual_name=piece.attr_qual_name,
            model_t=pyobj_creg.invite(piece.model_t),
            action_name=piece.action_name,
            key_fields=piece.key_fields,
            ctx_params=piece.ctx_params,
            service_params=piece.service_params,
            init_action_name=piece.init_action_name,
            )

    def __init__(self, module_name, attr_qual_name, model_t, action_name, key_fields, ctx_params, service_params, init_action_name):
        super().__init__(module_name, attr_qual_name, model_t, action_name, key_fields, ctx_params, service_params)
        self._init_action_name = init_action_name

    @property
    def piece(self):
        return htypes.crud_ctr.commit_ctr(
            module_name=self._module_name,
            attr_qual_name=tuple(self._attr_qual_name),
            model_t=pyobj_creg.actor_to_ref(self._model_t),
            action_name=self._action_name,
            key_fields=tuple(self._key_fields),
            ctx_params=tuple(self._ctx_params),
            service_params=tuple(self._service_params),
            init_action_name=self._init_action_name,
            )

    def update_resource_targets(self, resource_tgt, target_set):
        super().update_resource_targets(resource_tgt, target_set)
        self._add_open_command_targets(resource_tgt, target_set)

    def _add_open_command_targets(self, resource_tgt, target_set):
        if self._action_name == 'update':
            open_command_name = 'edit'
        else:
            open_command_name = self._action_name
        open_command_ctr = CrudOpenCommandCtr(
            module_name=self._module_name,
            model_t=self._model_t,
            name=open_command_name,
            )
        init_resolved_tgt = target_set.factory.config_item_resolved(
            self._service_name, self._make_resource_name('update', self._init_action_name))
        commit_resolved_tgt = target_set.factory.config_item_resolved(
            self._service_name, self._resource_name)
        open_command_ctr.update_open_command_targets(resource_tgt, target_set, init_resolved_tgt, commit_resolved_tgt)


class CrudOpenCommandCtr(ModuleCtr):

    def __init__(self, module_name, model_t, name):
        super().__init__(module_name)
        self._model_t = model_t
        self._name = name
        self._init_resolved_tgt = None
        self._commit_resolved_tgt = None

    def update_open_command_targets(self, resource_tgt, target_set, init_resolved_tgt, commit_resolved_tgt):
        _, resolved_tgt, _ = target_set.factory.config_items(
            'model_command_reg', self._resource_name, provider=resource_tgt, ctr=self)
        resolved_tgt.add_dep(init_resolved_tgt)
        resolved_tgt.add_dep(commit_resolved_tgt)
        resource_tgt.add_cfg_item_target(resolved_tgt)
        self._init_resolved_tgt = init_resolved_tgt
        self._commit_resolved_tgt = commit_resolved_tgt

    def get_component(self, name_to_res):
        return name_to_res[f'{self._resource_name}.command-cfg-item']

    def _command_d(self, types, name):
        code_name = self._module_name.split('.')[-1]
        d_t = d_type(types, code_name, name)
        return d_t()

    def make_component(self, types, python_module, name_to_res):
        key_fields = sorted(
            self._init_resolved_tgt.constructor.key_fields
            | self._commit_resolved_tgt.constructor.key_fields
            )
        init_action_fn = self._init_resolved_tgt.constructor.make_function(
            types, python_module, name_to_res)
        commit_action_fn = self._commit_resolved_tgt.constructor.make_function(
            types, python_module, name_to_res)
        value_t = self._init_resolved_tgt.constructor.value_t
        commit_command_d = self._command_d(types, self._commit_command_name)
        system_fn = htypes.crud.open_command_fn(
            name=self._name,
            value_t=pyobj_creg.actor_to_ref(value_t),
            key_fields=tuple(key_fields),
            init_action_fn=mosaic.put(init_action_fn),
            commit_command_d=mosaic.put(commit_command_d),
            commit_action_fn=mosaic.put(commit_action_fn),
            )
        open_command_d = self._command_d(types, self._name)
        properties = htypes.command.properties(
            is_global=False,
            uses_state=True,
            remotable=False,
            )
        command = htypes.command.model_command(
            d=mosaic.put(open_command_d),
            properties=properties,
            system_fn=mosaic.put(system_fn),
            preserve_remote=False,
            )
        template = htypes.command.command_template(
            command=mosaic.put(command),
            )
        cfg_item = htypes.cfg_item.typed_cfg_item(
            t=pyobj_creg.actor_to_ref(self._model_t),
            value=mosaic.put(template),
            )
        name_to_res[f'{self._resource_name}.open-command.d'] = open_command_d
        name_to_res[f'{self._resource_name}.commit-command.d'] = commit_command_d
        name_to_res[f'{self._resource_name}.command-fn'] = system_fn
        name_to_res[f'{self._resource_name}.command'] = command
        name_to_res[f'{self._resource_name}.command-template'] = template
        name_to_res[f'{self._resource_name}.command-cfg-item'] = cfg_item

    @property
    def _type_name(self):
        return f'{self._model_t.module_name}-{self._model_t.name}'

    @property
    def _resource_name(self):
        return f'{self._type_name}.{self._name}'
