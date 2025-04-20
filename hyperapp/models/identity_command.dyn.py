from functools import cached_property

from . import htypes
from .services import (
    mosaic,
    web,
    )
from .code.mark import mark
from .code.list_diff import IndexListDiff
from .code.directory import name_to_d
from .code.command import CommandKind, BoundCommandBase, UnboundCommandBase
from .code.model_command import model_command_ctx
from .code.command_list_model import command_item_to_model_item


class UnboundIdentityModelCommand(UnboundCommandBase):

    @classmethod
    @mark.actor.command_creg
    def from_piece(cls, piece):
        d = web.summon(piece.d)
        return cls(d)

    def __repr__(self):
        return f"<UnboundIdentityModelCommand>"

    @property
    def properties(self):
        return htypes.command.properties(
            is_global=False,
            uses_state=False,
            remotable=False,
            )

    def bind(self, ctx):
        return BoundIdentityModelCommand(self._d, ctx)


class BoundIdentityModelCommand(BoundCommandBase):

    @property
    def enabled(self):
        return not self._missing_params

    @property
    def disabled_reason(self):
        params = ", ".join(self._missing_params)
        return f"Params not ready: {params}"

    async def run(self):
        return self._ctx.model

    @cached_property
    def _missing_params(self):
        return {'model'} - self._ctx.as_dict().keys()


@mark.command
async def add_identity_command(piece, lcs, ctx, feed_factory, ui_model_command_items, shortcut_reg):
    feed = feed_factory(piece)
    model, model_t = web.summon_with_t(piece.model)
    model_state = web.summon(piece.model_state)
    command_ctx = model_command_ctx(ctx, model, model_state)
    commands_item_list = ui_model_command_items(lcs, model_t, command_ctx)
    command_d = name_to_d('custom_command', 'identity')
    model_command_piece = htypes.identity_command.identity_command(
        d=mosaic.put(command_d),
        )
    command_item = commands_item_list.add_custom_model_command(command_d, model_command_piece)
    new_item = command_item_to_model_item(shortcut_reg, lcs, command_item)
    await feed.send(IndexListDiff.Append(new_item))
