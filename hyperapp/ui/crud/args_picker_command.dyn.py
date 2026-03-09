import inspect

from .services import (
    mosaic,
    pyobj_creg,
    web,
    )
from .code.mark import mark
from .code.command_args import args_dict_to_tuple, args_t_dict_to_tuple, args_t_tuple_to_dict



def _can_crud_args(ctx):
    args = {}
    args['canned_item_piece'] = ctx.hook.canned_item_piece
    if 'model' in ctx:
        args['model'] = ctx.model
    if 'model_state' in ctx:
        args['model_state'] = ctx.model_state
    if 'element_idx' in ctx:
        args['element_idx'] = ctx.element_idx
    return args


@mark.ctx_actor.command_creg
async def args_picker_command(piece, ctx, navigator, crud, editor_default_reg):
    args = args_t_tuple_to_dict(piece.args)
    required_args = args_t_tuple_to_dict(piece.required_args)
    if len(required_args) > 1:
        required_str = ', '.join(name for name, t in required_args.items())
        raise RuntimeError(f"More than 1 args to pick is not supported: {required_str}")
    assert required_args  # Exactly one required arg type is expected.
    [(value_field, value_t)] = required_args.items()
    try:
        get_default_action = editor_default_reg[value_t]
    except KeyError:
        get_default_action = None
    commit_args = {**args, **_can_crud_args(ctx)}
    return await crud.open_view(
        navigator_rec=navigator,
        ctx=ctx,
        value_t=value_t,
        name=piece.name,
        label=f"{value_field} for: {piece.name}",
        init_action_ref=mosaic.put(get_default_action),
        commit_action_ref=piece.commit_command,
        commit_value_field=value_field,
        model=commit_args.get('model'),
        # remote_peer=remote_peer,
        commit_args=commit_args,
        )
