from .services import (
    mosaic,
    web,
    )
from .code.mark import mark
from .code.rpc_call import DEFAULT_TIMEOUT
from .code.command_args import args_tuple_to_dict, args_dict_to_tuple


@mark.ctx_actor.command_creg
def canned_args_command(piece, ctx, command_runner):
    command = web.summon(piece.commit_command)
    args = args_tuple_to_dict(piece.args)
    command_ctx = ctx.clone_with(**args)
    return command_runner.run_model_command(command_ctx, command)


def _pretify_arg_value(format, value):
    title = format(value)
    # Remove possible argument prefix.
    return title.split(': ')[-1]


@mark.actor.formatter_creg
def format_canned_arg_command_d(piece, format):
    commit_command_d = web.summon(piece.commit_command_d)
    commit_command_text = format(commit_command_d)
    args = [
        _pretify_arg_value(format, web.summon(arg.value))
        for arg in piece.args
        ]
    args_str = ", ".join(args)
    return f"{commit_command_text}: {args_str}"
