import inspect
import logging
from functools import partial

# from . import htypes
from .services import (
    deduce_t,
    mosaic,
    pyobj_creg,
    web,
    )
from .code.mark import mark
from .code.system_fn import ContextFn
from .code.list_diff import IndexListDiff, KeyListDiff
from .code.command import UnboundCommand, BoundCommand
from .code.command_enumerator import UnboundCommandEnumerator
from .code.config_ctl import FlatListConfigCtl, DictConfigCtl
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


@mark.service(ctl=TypeStrCommandConfigCtl())
def global_model_command_reg(config):
    return CommandDict(config)


@mark.service(ctl=TypeStrCommandConfigCtl())
def model_command_reg(config, model_t):
    return config.get(model_t, [])


@mark.service(ctl=DictConfigCtl(struct_ctl=ListStructCtl()))
def model_command_enumerator_reg(config, model_t):
    return config.get(model_t, [])


# @mark.service(ctl=FlatListConfigCtl())
# def global_model_command_enumerator_reg(config):
#     return CommandDict(config)


@mark.service
def get_model_commands(model_command_reg, model_command_enumerator_reg, model_t, ctx):
    command_list = [*model_command_reg(model_t)]
    for enumerator in model_command_enumerator_reg(model_t):
        command_list += enumerator.enum_commands(ctx)
    return command_list
