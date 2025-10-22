from . import htypes
from .services import (
    mosaic,
    )
from .code.rc_constructor import Constructor, ModuleCtr
from .code.init_hook_req import InitHookReq
from .code.ctx_actor_ctr import CtxFnCtr


class BaseInitHookCtr(Constructor):

    @classmethod
    def from_template_piece(cls, piece, service_name, var_name):
        return cls(var_name)

    def __init__(self, var_name):
        self._var_name = var_name

    def get_component(self, name_to_res):
        return name_to_res[self._var_name]

    @property
    def _fn_name(self):
        return self._var_name.rsplit('.', 1)[0]  # Drop .hook suffix.

    @property
    def key(self):
        return self._fn_name

    @property
    def req(self):
        return InitHookReq(self._fn_name)


class InitHookCtr(ModuleCtr, CtxFnCtr):

    _service_name = 'init_hook'

    @classmethod
    def from_piece(cls, piece):
        return cls(piece.module_name, piece.attr_qual_name, piece.service_params)

    def __init__(self, module_name, attr_qual_name, service_params):
        super().__init__(module_name)
        CtxFnCtr.__init__(self, attr_qual_name, ctx_params=(), service_params=service_params)

    @property
    def piece(self):
        return htypes.init_hook_ctr.init_hook_ctr(
            module_name=self._module_name,
            attr_qual_name=tuple(self._attr_qual_name),
            service_params=tuple(self._service_params),
            )

    def update_resource_targets(self, resource_tgt, target_set):
        ready_tgt, resolved_tgt, _ = target_set.factory.config_items(
            self._service_name, self._config_name,
            provider=resource_tgt,
            ctr=self,
            )
        resource_tgt.add_cfg_item_target(resolved_tgt)

    def get_component(self, name_to_res):
        return name_to_res[f'{self._fn_name}.{self._value_template_suffix}']

    def make_component(self, types, python_module, name_to_res=None):
        return self.make_value_template(python_module, name_to_res)

    @property
    def _config_name(self):
        return f'{self._module_name}-{self._fn_name}'

    @property
    def _fn_name(self):
        return '_'.join(self._attr_qual_name)
