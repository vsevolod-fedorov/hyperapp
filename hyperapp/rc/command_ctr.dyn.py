from functools import cached_property
from hyperapp.boot.htypes import TRecord

from . import htypes
from .services import (
    mosaic,
    pyobj_creg,
    )
from .code.rc_constructor import ModuleCtr
from .code.ctx_actor_ctr import CtxActorTemplateCtr
from .code.data_config_ctr import DataConfigCtr


STATE_PARAMS = {'state', 'model_state', 'current_item', 'current_idx', 'current_key', 'current_path'}
LOCAL_PARAMS = {'controller', 'ctx', 'lcs', 'rpc_endpoint', 'identity', 'remote_peer'}


def _is_state_param(name):
    return name in STATE_PARAMS or name.startswith('current_')


class CommandTemplateCtr(ModuleCtr):

    def __init__(self, module_name, attr_qual_name, service_name, enum_service_name, ctx_params, service_params, args):
        super().__init__(module_name)
        self._attr_qual_name = attr_qual_name
        self._service_name = service_name
        self._enum_service_name = enum_service_name
        self._ctx_params = ctx_params
        self._service_params = service_params
        self._args = args

    @property
    def _have_args(self):
        return bool(self._args)

    @property
    def _args_tuple(self):
        return tuple(
            htypes.command_resource.arg(
                name=name,
                t=pyobj_creg.actor_to_ref(t),
                )
            for name, t in self._args.items()
            )

    @staticmethod
    def _args_dict(arg_list):
        return {
            arg.name: pyobj_creg.invite(arg.t)
            for arg in arg_list
            }

    def update_resource_targets(self, resource_tgt, target_set):
        if self._have_args:
            service_name = self._enum_service_name
            if not service_name:
                attr_path = ".".join(self._attr_qual_name)
                raise RuntimeError(
                    f"Command arguments are not supported for {self._service_name} commands:"
                    f" {self._module_name}:{attr_path}")
        else:
            service_name = self._service_name
        # ready target may already have provider set, but in case of
        # non-typed marker it have not.
        _, reg_resolved_tgt, _ = target_set.factory.config_items(
            service_name, self._resource_name,
            provider=resource_tgt,
            ctr=self,
            )
        self._create_group_ctr(resource_tgt, target_set)
        # resource target may already have resolved target, but in case of
        # non-typed marker it have not.
        resource_tgt.add_cfg_item_target(reg_resolved_tgt)
        actor_ctr = CtxActorTemplateCtr(
            module_name=self._module_name,
            attr_qual_name=self._attr_qual_name,
            service_name=self._actor_creg,
            t=self._command_t,
            ctx_params=self._ctx_params,
            service_params=self._service_params,
            create_t=True,
            )
        actor_ctr.update_resource_targets(resource_tgt, target_set)

    def get_component(self, name_to_res):
        return name_to_res[f'{self._resource_name}.command-cfg-item']

    @property
    def _command_full_name(self):
        return '_'.join(self._attr_qual_name)

    @property
    def _command_last_name(self):
        return self._attr_qual_name[-1]

    @cached_property
    def _command_t(self):
        code_name = self._module_name.split('.')[-1]
        return TRecord(code_name, self._command_full_name)


class CommandMixin:

    def _create_group_ctr(self, resource_tgt, target_set):
        group_ctr = DataConfigCtr(
            module_name=self._module_name,
            service_name='command_group_reg',
            name=self._command_key_name,
            key_resource_suffix='command-key',
            value_resource_suffix='command-group',
            item_resource_suffix='command-group-item',
            key=self._command_key,
            value=self._command_group,
            )
        group_ctr.update_resource_targets(resource_tgt, target_set)

    def _make_args_picker_command_enum(self, commit_command):
        required_args = tuple(
            htypes.command.arg_t(
                name=name,
                t=pyobj_creg.actor_to_ref(t),
                )
            for name, t in self._args.items()
            )
        return htypes.command.args_picker_command_enum(
            name=self._command_last_name,
            required_args=required_args,
            commit_command=mosaic.put(commit_command),
            )

    def _make_command(self, name_to_res):
        if self._have_args:
            commit_command = self._command_t()
            command_enum = self._make_args_picker_command_enum(commit_command)
            if name_to_res is not None:
                name_to_res[f'{self._command_full_name}.commit-command'] = commit_command
                name_to_res[f'{self._command_full_name}.command-enum'] = command_enum
            return command_enum
        else:
            command = self._command_t()
            if name_to_res is not None:
                name_to_res[f'{self._command_full_name}.command'] = command
            return command


class EnumMixin:

    def _create_group_ctr(self, resource_tgt, target_set):
        pass

    def _make_command(self, name_to_res):
        assert not self._have_args  # No args are possible for enumerators.
        command_enum = self._command_t()
        if name_to_res is not None:
            name_to_res[f'{self._command_full_name}.command-enum'] = command_enum
        return command_enum


class UntypedCommandTemplateCtr(CommandTemplateCtr):

    @classmethod
    def from_piece(cls, piece):
        return cls(
            module_name=piece.module_name,
            attr_qual_name=piece.attr_qual_name,
            service_name=piece.service_name,
            enum_service_name=piece.enum_service_name,
            ctx_params=piece.ctx_params,
            service_params=piece.service_params,
            args=cls._args_dict(piece.args),
            )

    @property
    def piece(self):
        return self._template_ctr_t(
            module_name=self._module_name,
            attr_qual_name=tuple(self._attr_qual_name),
            service_name=self._service_name,
            enum_service_name=self._enum_service_name,
            ctx_params=tuple(self._ctx_params),
            service_params=tuple(self._service_params),
            args=self._args_tuple,
            )

    def make_component(self, types, python_module, name_to_res=None):
        command = self._make_command(name_to_res)
        cfg_item = htypes.cfg_item.str_cfg_item(
            key=self._command_last_name,
            value=mosaic.put(command),
            )
        if name_to_res is not None:
            name_to_res[f'{self._resource_name}.command-cfg-item'] = cfg_item
        return cfg_item

    @property
    def _resource_name(self):
        return self._command_full_name


class TypedCommandTemplateCtr(CommandTemplateCtr):

    @classmethod
    def from_piece(cls, piece):
        return cls(
            module_name=piece.module_name,
            attr_qual_name=piece.attr_qual_name,
            service_name=piece.service_name,
            enum_service_name=piece.enum_service_name,
            ctx_params=piece.ctx_params,
            service_params=piece.service_params,
            args=cls._args_dict(piece.args),
            t=pyobj_creg.invite(piece.t),
            )

    def __init__(self, module_name, attr_qual_name, service_name, enum_service_name, ctx_params, service_params, args, t):
        super().__init__(module_name, attr_qual_name, service_name, enum_service_name, ctx_params, service_params, args)
        self._t = t

    @property
    def piece(self):
        return self._template_ctr_t(
            module_name=self._module_name,
            attr_qual_name=tuple(self._attr_qual_name),
            service_name=self._service_name,
            enum_service_name=self._enum_service_name,
            ctx_params=tuple(self._ctx_params),
            service_params=tuple(self._service_params),
            args=self._args_tuple,
            t=pyobj_creg.actor_to_ref(self._t),
            )

    def make_component(self, types, python_module, name_to_res=None):
        command = self._make_command(name_to_res)
        cfg_item = htypes.command.type_str_command(
            t=pyobj_creg.actor_to_ref(self._t),
            name=self._command_last_name,
            command=mosaic.put(command),
            )
        if name_to_res is not None:
            name_to_res[f'{self._resource_name}.command-cfg-item'] = cfg_item
        return cfg_item

    @property
    def _type_name(self):
        return f'{self._t.module_name}-{self._t.name}'

    @property
    def _command_key_name(self):
        return f'{self._type_name}-{self._command_full_name}'

    @property
    def _resource_name(self):
        return f'{self._type_name}-{self._command_full_name}'


class UiCommandTemplateCtr(TypedCommandTemplateCtr, CommandMixin):

    _command_fn_t = htypes.system_fn.ctx_fn
    _template_ctr_t = htypes.command_resource.ui_command_template_ctr
    _actor_creg = 'command_creg'

    @property
    def _command_key(self):
        return htypes.command.ui_command_key(
            view_t=pyobj_creg.actor_to_ref(self._t),
            name=self._command_full_name,
            )

    @property
    def _command_group(self):
        return 'view'


class UniversalUiCommandTemplateCtr(UntypedCommandTemplateCtr):

    # _command_t = htypes.command.ui_command
    _command_fn_t = htypes.system_fn.ctx_fn
    _template_ctr_t = htypes.command_resource.universal_ui_command_template_ctr
    # _is_global = False
    # _direct_command_resource_suffix = 'universal-ui-command'
    # _command_enum_resource_suffix = 'universal-ui-command-enumerator'


class UiCommandEnumeratorTemplateCtr(TypedCommandTemplateCtr):

    _template_ctr_t = htypes.command_resource.ui_command_enumerator_template_ctr
    _command_fn_t = htypes.command.ui_command_enum_fn

    def _make_command(self, types, name, fn, name_to_res):
        if name_to_res is not None:
            name_to_res[f'{self._fn_name}.fn'] = fn
        return htypes.command.ui_command_enumerator(
            system_fn=mosaic.put(fn),
            )


class ModelCommandTemplateCtr(TypedCommandTemplateCtr, CommandMixin):

    _actor_creg = 'command_creg'

    @classmethod
    def from_piece(cls, piece):
        return cls(
            module_name=piece.module_name,
            attr_qual_name=piece.attr_qual_name,
            service_name=piece.service_name,
            enum_service_name=piece.enum_service_name,
            ctx_params=piece.ctx_params,
            service_params=piece.service_params,
            args=cls._args_dict(piece.args),
            preserve_remote=piece.preserve_remote,
            t=pyobj_creg.invite(piece.t),
            command_fn_t=pyobj_creg.invite(piece.command_fn_t),
            )

    def __init__(self, module_name, attr_qual_name, service_name, enum_service_name, ctx_params, service_params, args, preserve_remote, t, command_fn_t):
        super().__init__(module_name, attr_qual_name, service_name, enum_service_name, ctx_params, service_params, args, t)
        self._preserve_remote = preserve_remote
        self._command_fn_t = command_fn_t

    @property
    def piece(self):
        return htypes.command_resource.model_command_template_ctr(
            module_name=self._module_name,
            attr_qual_name=tuple(self._attr_qual_name),
            service_name=self._service_name,
            enum_service_name=self._enum_service_name,
            ctx_params=tuple(self._ctx_params),
            service_params=tuple(self._service_params),
            args=self._args_tuple,
            preserve_remote=self._preserve_remote,
            t=pyobj_creg.actor_to_ref(self._t),
            command_fn_t=pyobj_creg.actor_to_ref(self._command_fn_t),
            )


    @property
    def _command_key(self):
        return htypes.command.model_command_key(
            model_t=pyobj_creg.actor_to_ref(self._t),
            name=self._command_full_name,
            )

    @property
    def _command_group(self):
        if set(self._ctx_params) & STATE_PARAMS:
            return 'context'
        else:
            return 'model'


class ModelCommandEnumeratorTemplateCtr(TypedCommandTemplateCtr, EnumMixin):

    _template_ctr_t = htypes.command_resource.model_command_enumerator_template_ctr
    _actor_creg = 'command_enum_creg'


class GlobalModelCommandTemplateCtr(UntypedCommandTemplateCtr, CommandMixin):

    _command_fn_t = htypes.command.model_command_fn
    _actor_creg = 'command_creg'

    @classmethod
    def from_piece(cls, piece):
        return cls(
            module_name=piece.module_name,
            attr_qual_name=piece.attr_qual_name,
            service_name=piece.service_name,
            enum_service_name=piece.enum_service_name,
            ctx_params=piece.ctx_params,
            service_params=piece.service_params,
            args=cls._args_dict(piece.args),
            preserve_remote=piece.preserve_remote,
            )

    def __init__(self, module_name, attr_qual_name, service_name, enum_service_name, ctx_params, service_params, args, preserve_remote):
        super().__init__(module_name, attr_qual_name, service_name, enum_service_name, ctx_params, service_params, args)
        self._preserve_remote = preserve_remote

    @property
    def piece(self):
        return htypes.command_resource.global_model_command_template_ctr(
            module_name=self._module_name,
            attr_qual_name=tuple(self._attr_qual_name),
            service_name=self._service_name,
            enum_service_name=self._enum_service_name,
            ctx_params=tuple(self._ctx_params),
            service_params=tuple(self._service_params),
            args=self._args_tuple,
            preserve_remote=self._preserve_remote,
            )

    @property
    def _command_key_name(self):
        return self._command_full_name

    @property
    def _command_key(self):
        return htypes.command.global_model_command_key(self._command_full_name)

    @property
    def _command_group(self):
        if set(self._ctx_params) & STATE_PARAMS:
            return 'context'
        else:
            return 'global'
