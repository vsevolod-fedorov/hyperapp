import inspect
import logging

from hyperapp.boot.htypes.deduce_value_type import DeduceTypeError

from . import htypes
from .services import (
    deduce_t,
    mosaic,
    web,
    )
from .code.mark import mark
from .code.arg_mark import model_mark_prefix, value_mark_name
from .code.command_args import args_dict_to_tuple, args_t_tuple_to_dict

log = logging.getLogger(__name__)


def _pick_value_mark_by_type(ctx, required_t):
    ctx_name = value_mark_name(required_t)
    try:
        value = ctx[ctx_name]
    except KeyError:
        return None
    try:
        value_t = deduce_t(value)
    except DeduceTypeError:
        return None
    if required_t is value_t:
        return value
    return None


def _pick_any_model_mark(ctx):
    for name, value in reversed(ctx.items()):
        if name.startswith(model_mark_prefix):
            return mosaic.put(value)
    return None


def _pick_args_from_context(required_arg_types, ctx):
    args = {}
    required_args = {}
    for name, t in required_arg_types.items():
        if t is htypes.builtin.ref:
            value = _pick_any_model_mark(ctx)
        else:
            value = _pick_value_mark_by_type(ctx, t)
        if value is None:
            required_args[name] = t
        else:
            args[name] = value
    return (args, required_args)


def _canned_args_command(command_factory, ctx, name, args, commit_command_ref):
    command = htypes.command.canned_args_command(
        args=args_dict_to_tuple(args),
        commit_command=commit_command_ref,
        )
    return command_factory(
        key=htypes.command.canned_args_command_key(name),
        name=name,
        command=command,
        ctx=ctx.pop(),
        )


@mark.ctx_actor.command_enum_creg
def args_picker_command_enum(piece, ctx, command_factory):
    required_arg_types = args_t_tuple_to_dict(piece.required_args)
    log.debug("Args picker command enum: %s", required_arg_types)
    args, required_args = _pick_args_from_context(required_arg_types, ctx)
    if htypes.builtin.ref in required_args.values():
        log.warning("Args picker for references is not yet implemented")
        result = []
    else:
        if required_args:
            return []  # TODO: Implement args picker command
            command = self._args_picker_command(args, required_args)
        else:
            command = _canned_args_command(command_factory, ctx, piece.name, args, piece.commit_command)
        result = [command]
    log.debug("Args picker command enum result: %r", result)
    return result


@mark.actor.formatter_creg
def format_open_args_picker_command_d(piece, format):
    commit_command_d = web.summon(piece.commit_command_d)
    commit_command_text = format(commit_command_d)
    return f"{commit_command_text}..."
