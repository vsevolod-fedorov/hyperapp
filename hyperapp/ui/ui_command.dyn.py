import logging
from functools import partial

from hyperapp.boot.htypes import TRecord

from . import htypes
from .services import (
    deduce_t,
    mosaic,
    pyobj_creg,
    web,
    )
from .code.mark import mark
from .code.config_ctl import DictConfigCtl, FlatListConfigCtl
from .code.config_struct_ctl import ListStructCtl
from .code.command_config_ctl import TypeStrCommandConfigCtl
from .code.command import prepare_command_ctx

log = logging.getLogger(__name__)


def _item_dict_with_bases(config, view_t):
    item_dict = {}
    while view_t:
        item_dict.update(config.get(view_t, {}))
        if not isinstance(view_t, TRecord):
            break
        view_t = view_t.base
    return item_dict


def _item_list_with_bases(config, view_t):
    item_list = []
    while view_t:
        item_list += config.get(view_t, [])
        if not isinstance(view_t, TRecord):
            break
        view_t = view_t.base
    return item_list


@mark.service(ctl=TypeStrCommandConfigCtl())
def view_ui_command_reg(config, view_t):
    return _item_dict_with_bases(config, view_t)


@mark.service(ctl=TypeStrCommandConfigCtl())
def view_element_ui_command_reg(config, view_t):
    return _item_dict_with_bases(config, view_t)


# @mark.service(ctl=DictConfigCtl(struct_ctl=ListStructCtl()))
# def view_element_ui_command_enumerator_reg(config, view_t):
#     return _item_list_with_bases(config, view_t)


# # UI commands returning model.
# @mark.service(ctl=DictConfigCtl(struct_ctl=ListStructCtl()))
# def view_ui_model_command_reg(config, view_t):
#     return _item_list_with_bases(config, view_t)


# @mark.service(ctl=FlatListConfigCtl())
# def universal_ui_command_reg(config):
#     return config


@mark.service(ctl=TypeStrCommandConfigCtl())
def ui_command_enumerator_reg(config, view_t):
    return _item_dict_with_bases(config, view_t)


# @mark.service(ctl=FlatListConfigCtl())
# def universal_ui_command_enumerator_reg(config):
#     return config


@mark.service
def get_view_commands(
        # diff_creg,
        # feed_factory,
        # error_view,
        # view_reg,
        # visualizer,
        command_factory,
        command_enum_creg,
        view_ui_command_reg,
        # view_ui_model_command_reg,
        # universal_ui_command_reg,
        ui_command_enumerator_reg,
        # universal_ui_command_enumerator_reg,
        ctx,
        view,
        ):
    view_t = deduce_t(view.piece)
    view_t_ref = pyobj_creg.actor_to_ref(view_t)
    name_to_command = view_ui_command_reg(view_t)
    command_list = [
        command_factory(
            key=htypes.command.ui_command_key(view_t_ref, name),
            name=name,
            command=command,
            ctx=ctx,
            )
        for name, command in name_to_command.items()
        ]
    enum_ctx = prepare_command_ctx(ctx)
    for name, enum in ui_command_enumerator_reg(view_t).items():
        command_list += command_enum_creg.animate(enum, enum_ctx)
    return command_list

    # ui_model_command_list = [
    #     wrap_model_command_to_ui_command(diff_creg, feed_factory, error_view, view_reg, visualizer, cmd)
    #     for cmd in view_ui_model_command_reg(view_t)
    #     ]
    # command_list = [
    #     *view_ui_command_reg(view_t),
    #     *ui_model_command_list,
    #     *universal_ui_command_reg,
    #     ]
    # for enumerator in ui_command_enumerator_reg(view_t):
    #     command_list += enumerator.enum_commands(ctx)
    # for enumerator in universal_ui_command_enumerator_reg:
    #     command_list += enumerator.enum_commands(ctx)
    # return command_list


@mark.service
def get_view_element_commands(
        command_factory,
        view_element_ui_command_reg,
        # view_element_ui_command_enumerator_reg,
        ctx,
        view,
        ):
    view_t = deduce_t(view.piece)
    view_t_ref = pyobj_creg.actor_to_ref(view_t)
    name_to_command = view_element_ui_command_reg(view_t)
    return [
        command_factory(
            key=htypes.command.ui_command_key(view_t_ref, name),
            name=name,
            command=command,
            ctx=ctx,
            )
        for name, command in name_to_command.items()
        ]
