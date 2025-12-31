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


def command_item_to_model_item(shortcut_reg, lcs, item):
    return htypes.command_list_model.item(
        ui_command_d=mosaic.put(item.d),
        model_command_d=mosaic.put(item.model_command_d),
        name=item.name,
        groups=", ".join(d_to_name(g) for g in item.command.groups) if item.enabled else "",
        repr=repr(item.command),
        shortcut=shortcut_reg.get(item.d) or "",
        text=_get_command_text(lcs, item.d),
        tooltip=_get_command_tooltip(lcs, item.d),
        )


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


def _view_item(cmd, get_command_group, shortcut_reg):
    key = web.summon(cmd.key)
    shortcut = shortcut_reg.get(key)
    return htypes.command_list_model.item(
        name=cmd.name,
        groups=get_command_group(web.summon(cmd.key)) or '',
        shortcut=shortcut or "",
        text="",
        tooltip="",
        bound_command=mosaic.put(cmd),
    )


@mark.model
def commands_model(piece, get_command_group, shortcut_reg):
    return [
        _view_item(cmd, get_command_group, shortcut_reg)
        for cmd in piece.commands
    ]


@mark.global_command
def open_commands(commands):
    return htypes.command_list_model.model(
        commands=tuple(
            htypes.command_list_model.bound_command(
                name=cmd.name,
                key=mosaic.put(cmd.key),
                model=mosaic.put_opt(cmd.ctx.get('model')),
                model_state=mosaic.put_opt(cmd.ctx.get('model_state')),
            )
            for cmd in commands
        ),
    )


def _set_shortcut(current_idx, key, cmd, shortcut, hook, feed, get_command_group, shortcut_reg):
    log.info("Set shortcut for %s: %r", key, shortcut)
    shortcut_reg[key] = shortcut
    new_item = _view_item(cmd, get_command_group, shortcut_reg)
    feed.send(IndexListDiff.Replace(current_idx, new_item))
    hook.parent_context_changed()


@mark.command
def set_shortcut(model, current_idx, current_item, hook, feed_factory, get_command_group, shortcut_reg):
    feed = feed_factory(model)
    cmd = web.summon(current_item.bound_command)
    key = web.summon(cmd.key)
    shortcut = run_key_input_dialog()
    if not shortcut:
        return
    _set_shortcut(current_idx, key, cmd, shortcut, hook, feed, get_command_group, shortcut_reg)


@mark.command
def set_escape_shortcut(model, current_idx, current_item, hook, feed_factory, get_command_group, shortcut_reg):
    feed = feed_factory(model)
    cmd = web.summon(current_item.bound_command)
    key = web.summon(cmd.key)
    shortcut = 'Esc'
    _set_shortcut(current_idx, key, cmd, shortcut, hook, feed, get_command_group, shortcut_reg)


@mark.command
def remove_shortcut(model, current_idx, current_item, hook, feed_factory, get_command_group, shortcut_reg):
    feed = feed_factory(model)
    cmd = web.summon(current_item.bound_command)
    key = web.summon(cmd.key)
    log.info("Remove shortcut for %s", key)
    del shortcut_reg[key]
    new_item = _view_item(cmd, get_command_group, shortcut_reg)
    feed.send(IndexListDiff.Replace(current_idx, new_item))
    hook.parent_context_changed()


@mark.actor.formatter_creg
def format_model(piece):
    return "Commands"
