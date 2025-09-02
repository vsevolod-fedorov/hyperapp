import logging

from hyperapp.boot.htypes import TList

from . import htypes
from .services import (
    code_registry_ctr,
    deduce_t,
    mosaic,
    pyobj_creg,
    web,
    )
from .code.mark import mark

log = logging.getLogger(__name__)


def _primitive_value_layout(t):
    if isinstance(t, TList):
        adapter = htypes.list_adapter.static_list_adapter()
        return htypes.list.view(mosaic.put(adapter))
    raise KeyError(t)


@mark.service
def model_reg(config):
    return config


@mark.service
def visualizer_reg(system_fn_creg, model_reg, t):
    try:
        model = model_reg[t]
    except KeyError:
        raise
    ui_t = web.summon(model.ui_t)
    system_fn = system_fn_creg.invite(model.system_fn)
    return (ui_t, system_fn)


@mark.service
def ui_type_creg(config):
    return code_registry_ctr('ui_type_creg', config)


@mark.service
def visualizer(model_layout_reg, visualizer_reg, ui_type_creg, model_t):
    layout_k = htypes.ui.model_layout_k(
        model_t=pyobj_creg.actor_to_ref(model_t),
        )
    try:
        return model_layout_reg[layout_k]
    except KeyError:
        pass
    try:
        return _primitive_value_layout(model_t)
    except KeyError:
        pass
    try:
        ui_t, system_fn = visualizer_reg(model_t)
    except KeyError:
        raise RuntimeError(f"No view is known for model: {model_t!r}")
    return ui_type_creg.animate(ui_t, system_fn)


@mark.actor.resource_name_creg
def model_layout_k_resource_name(piece, gen):
    model_t = pyobj_creg.invite(piece.model_t)
    return f'{model_t.full_name}-model_layout_k'


@mark.actor.formatter_creg
def format_model_layout_k(piece):
    model_t = pyobj_creg.invite(piece.model_t)
    return f'model_layout_k({model_t.full_name})'
