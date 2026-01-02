import logging

from . import htypes
from .services import (
    mosaic,
    web,
    )
from .code.mark import mark
from .code.list_diff import IndexListDiff
from .code.directory import d_to_name
from .code.key_input_dialog import run_key_input_dialog

log = logging.getLogger(__name__)


def _get_command_text(lcs, d):
    return ""


def _get_command_tooltip(lcs, d):
    return ""


@mark.crud.get
def command_get(piece, ui_command_d, lcs):
    return htypes.command_list_model.form(
        text="",
        tooltip="",
        )


@mark.crud.update
def command_update(piece, ui_command_d, value, lcs):
    d = web.summon(ui_command_d)
    prev_text = _get_command_text(lcs, d)
    prev_tooltip = _get_command_tooltip(lcs, d)
    if value.text != prev_text:
        log.info("Set text for %s: %r", d, value.text)
    if value.tooltip != prev_tooltip:
        log.info("Set tooltip for %s: %r", d, value.tooltip)


def _view_item(bcmd, get_command_group, shortcut_reg):
    key = web.summon(bcmd.key)
    shortcut = shortcut_reg.get(key)
    return htypes.command_list_model.item(
        name=bcmd.name,
        groups=get_command_group(web.summon(bcmd.key)) or '',
        shortcut=shortcut or "",
        text="",
        tooltip="",
        bound_command=mosaic.put(bcmd),
    )


@mark.model
def commands_model(model, get_command_group, shortcut_reg):
    return [
        _view_item(bcmd, get_command_group, shortcut_reg)
        for bcmd in model.commands
    ]


@mark.global_command
def open_commands(commands):
    return htypes.command_list_model.model(
        commands=tuple(
            htypes.command_list_model.bound_command(
                name=cmd.name,
                key=mosaic.put(cmd.key),
                command=mosaic.put(cmd.command),
                model=mosaic.put_opt(cmd.ctx.get('model')),
                model_state=mosaic.put_opt(cmd.ctx.get('model_state')),
            )
            for cmd in commands
        ),
    )


def _set_shortcut(current_idx, key, bcmd, shortcut, hook, feed, get_command_group, shortcut_reg):
    log.info("Set shortcut for %s: %r", key, shortcut)
    shortcut_reg[key] = shortcut
    new_item = _view_item(bcmd, get_command_group, shortcut_reg)
    feed.send(IndexListDiff.Replace(current_idx, new_item))
    hook.parent_context_changed()


@mark.command
def set_shortcut(model, current_idx, current_item, hook, feed_factory, get_command_group, shortcut_reg):
    feed = feed_factory(model)
    bcmd = web.summon(current_item.bound_command)
    key = web.summon(bcmd.key)
    shortcut = run_key_input_dialog()
    if not shortcut:
        return
    _set_shortcut(current_idx, key, bcmd, shortcut, hook, feed, get_command_group, shortcut_reg)


@mark.command
def set_escape_shortcut(model, current_idx, current_item, hook, feed_factory, get_command_group, shortcut_reg):
    feed = feed_factory(model)
    bcmd = web.summon(current_item.bound_command)
    key = web.summon(bcmd.key)
    shortcut = 'Esc'
    _set_shortcut(current_idx, key, bcmd, shortcut, hook, feed, get_command_group, shortcut_reg)


@mark.command
def remove_shortcut(model, current_idx, current_item, hook, feed_factory, get_command_group, shortcut_reg):
    feed = feed_factory(model)
    bcmd = web.summon(current_item.bound_command)
    key = web.summon(bcmd.key)
    log.info("Remove shortcut for %s", key)
    del shortcut_reg[key]
    new_item = _view_item(bcmd, get_command_group, shortcut_reg)
    feed.send(IndexListDiff.Replace(current_idx, new_item))
    hook.parent_context_changed()


@mark.command
async def run_command(model, current_item, ctx, command_factory):
    bcmd = web.summon(current_item.bound_command)
    key = web.summon(bcmd.key)
    if isinstance(key, htypes.command.ui_command_key):
    # View commands not supported - their view, widget, hook and state are not yet preserved in bound command.
        return
    kw = {}
    if bcmd.model is not None:
        kw['model'] = web.summon(bcmd.model)
    if bcmd.model_state is not None:
        kw['model_state'] = web.summon(bcmd.model_state)
    ctx = ctx.pop().push(**kw)  # Replace this-command-specific items.
    command = command_factory(
        key=web.summon(bcmd.key),
        name=bcmd.name,
        command=web.summon(bcmd.command),
        ctx=ctx,
        )
    await command.run()


@mark.actor.formatter_creg
def format_model(piece):
    return "Commands"
