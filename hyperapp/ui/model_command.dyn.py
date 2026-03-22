import inspect
import logging
from functools import partial

from . import htypes
from .services import (
    deduce_t,
    mosaic,
    pyobj_creg,
    web,
    )
from .code.mark import mark
from .code.system_fn import ContextFn
from .code.list_diff import IndexListDiff, KeyListDiff
from .code.command import prepare_command_ctx
from .code.command_enumerator import UnboundCommandEnumerator
from .code.config_ctl import DataValueCtl, DictConfigCtl
from .code.config_key_ctl import StrKeyCtl
from .code.config_struct_ctl import ListStructCtl
from .code.command_config_ctl import TypeStrCommandConfigCtl

log = logging.getLogger(__name__)


def model_command_ctx(ctx, model, model_state):
    return ctx.push(
        model=model,
        piece=model,
        model_state=model_state,
        **ctx.attributes(model_state),
        )


@mark.service(ctl=DictConfigCtl(key_ctl=StrKeyCtl(), value_ctl=DataValueCtl()))
def global_model_command_reg(config):
    return config


@mark.service
def get_global_model_commands(command_factory, global_model_command_reg, ctx):
    name_to_command = global_model_command_reg
    return [
        command_factory(
            key=htypes.command.global_model_command_key(name),
            name=name,
            command=command,
            ctx=ctx,
            )
        for name, command in name_to_command.items()
        ]


@mark.service(ctl=TypeStrCommandConfigCtl())
def model_command_reg(config, model_t):
    return config.get(model_t, {})


# TODO: Make it back to flat list instead of name -> piece dict.
@mark.service(ctl=TypeStrCommandConfigCtl())
def model_command_enumerator_reg(config, model_t):
    return config.get(model_t, {})


# @mark.service(ctl=FlatListConfigCtl())
# def global_model_command_enumerator_reg(config):
#     return CommandDict(config)


@mark.service
def get_model_commands(
        command_factory,
        model_command_reg,
        model_command_enumerator_reg,
        command_enum_creg,
        model_t,
        ctx,
        ):
    name_to_command = model_command_reg(model_t)
    model_t_ref = pyobj_creg.actor_to_ref(model_t)

    def key_factory(name):
        return htypes.command.model_command_key(model_t_ref, name)

    command_list = [
        command_factory(
            key=key_factory(name),
            name=name,
            command=command,
            ctx=ctx,
            )
        for name, command in name_to_command.items()
        ]
    enum_ctx = prepare_command_ctx(ctx).clone_with(
        key_factory=key_factory,
        )
    for name, enum in model_command_enumerator_reg(model_t).items():
        command_list += command_enum_creg.animate(enum, enum_ctx)
    return command_list
