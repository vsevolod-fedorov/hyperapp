from . import htypes
from .services import (
    mosaic,
    pyobj_creg,
    )
from .code.ctx_actor_ctr import CtxActorProbeMixin, CtxActorTemplateCtr
from .code.cfg_item_req import CfgItemReq


class ViewTemplateCtr(CtxActorTemplateCtr):

    @classmethod
    def from_piece(cls, piece):
        return cls(
            module_name=piece.module_name,
            attr_qual_name=piece.attr_qual_name,
            t=pyobj_creg.invite(piece.t),
            ctx_params=piece.ctx_params,
            service_params=piece.service_params,
            )

    def __init__(self, module_name, attr_qual_name, t, ctx_params, service_params):
        super().__init__(
            module_name=module_name,
            attr_qual_name=attr_qual_name,
            service_name='view_reg',
            t=t,
            ctx_params=ctx_params,
            service_params=service_params,
            )

    @property
    def piece(self):
        return htypes.view_ctr.template_ctr(
            module_name=self._module_name,
            attr_qual_name=tuple(self._attr_qual_name),
            t=pyobj_creg.actor_to_ref(self._t),
            ctx_params=tuple(self._ctx_params),
            service_params=tuple(self._service_params),
            )

    @property
    def ctx_params(self):
        return self._ctx_params

    @property
    def _resource_name(self):
        return f'{self._type_name}.view-cfg-item'
