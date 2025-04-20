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
from .code.system_fn import ContextFn
from .code.command import UnboundCommand, BoundCommand, CommandKind
from .code.command_enumerator import UnboundCommandEnumerator
from .code.command_groups import default_command_groups
from .code.list_config_ctl import DictListConfigCtl, FlatListConfigCtl
from .code.ui_model_command import wrap_model_command_to_ui_command

log = logging.getLogger(__name__)


class UiCommandEnumFn(ContextFn):

    @classmethod
    @mark.actor.system_fn_creg
    def from_piece(cls, piece, system, rpc_system_call_factory):
        return super().from_piece(piece, system, rpc_system_call_factory)

    @property
    def piece(self):
        return htypes.command.ui_command_enum_fn(
            function=pyobj_creg.actor_to_ref(self._raw_fn),
            ctx_params=tuple(self._ctx_params),
            service_params=tuple(self._service_params),
            )

    def call(self, ctx, **kw):
        result = super().call(ctx, **kw)
        return self._prepare_result(result)

    @staticmethod
    def _prepare_result(result):
        if result is None:
            return result
        if type(result) is list:
            result = tuple(result)
        return result


class UnboundUiCommand(UnboundCommand):

    def __init__(self, d, ctx_fn, properties, groups):
        super().__init__(d, ctx_fn)
        self._properties = properties
        self._groups = groups

    @property
    def piece(self):
        return htypes.command.ui_command(
            d=mosaic.put(self._d),
            properties=self._properties,
            system_fn=mosaic.put(self._ctx_fn.piece),
            )

    @property
    def properties(self):
        return self._properties

    def bind(self, ctx):
        return BoundUiCommand(self._d, self._ctx_fn, ctx, self._properties, self._groups)


class BoundUiCommand(BoundCommand):

    def __init__(self, d, ctx_fn, ctx, properties, groups):
        super().__init__(d, ctx_fn, ctx)
        self._properties = properties
        self._groups = groups

    @property
    def properties(self):
        return self._properties

    @property
    def groups(self):
        return self._groups


@mark.actor.command_creg
def ui_command_from_piece(piece, system_fn_creg):
    ctx_fn = system_fn_creg.invite(piece.system_fn)
    return UnboundUiCommand(
        d=web.summon(piece.d),
        ctx_fn=ctx_fn,
        properties=piece.properties,
        groups=default_command_groups(piece.properties, CommandKind.VIEW),
        )


@mark.actor.command_creg
def ui_command_enumerator_from_piece(piece, system_fn_creg):
    ctx_fn = system_fn_creg.invite(piece.system_fn)
    return UnboundCommandEnumerator(
        ctx_fn=ctx_fn,
        )


def _commands_with_bases(config, view_t):
    command_list = []
    while view_t:
        command_list += config.get(view_t, [])
        if not isinstance(view_t, TRecord):
            break
        view_t = view_t.base
    return command_list


@mark.service(ctl=DictListConfigCtl())
def view_ui_command_reg(config, view_t):
    return _commands_with_bases(config, view_t)


@mark.service(ctl=DictListConfigCtl())
def view_element_ui_command_reg(config, view_t):
    return _commands_with_bases(config, view_t)


@mark.service(ctl=DictListConfigCtl())
def view_element_ui_command_enumerator_reg(config, view_t):
    return _commands_with_bases(config, view_t)


# UI commands returning model.
@mark.service(ctl=DictListConfigCtl())
def view_ui_model_command_reg(config, view_t):
    return config.get(view_t, [])


@mark.service(ctl=FlatListConfigCtl())
def universal_ui_command_reg(config):
    return config


@mark.service(ctl=DictListConfigCtl())
def ui_command_enumerator_reg(config, view_t):
    return config.get(view_t, [])


@mark.service(ctl=FlatListConfigCtl())
def universal_ui_command_enumerator_reg(config):
    return config


@mark.service
def get_view_commands(
        diff_creg,
        feed_factory,
        error_view,
        view_reg,
        visualizer,
        view_ui_command_reg,
        view_ui_model_command_reg,
        universal_ui_command_reg,
        ui_command_enumerator_reg,
        universal_ui_command_enumerator_reg,
        ctx,
        view,
        ):
    view_t = deduce_t(view.piece)
    ui_model_command_list = [
        wrap_model_command_to_ui_command(diff_creg, feed_factory, error_view, view_reg, visualizer, cmd)
        for cmd in view_ui_model_command_reg(view_t)
        ]
    command_list = [
        *view_ui_command_reg(view_t),
        *ui_model_command_list,
        *universal_ui_command_reg,
        ]
    for enumerator in ui_command_enumerator_reg(view_t):
        command_list += enumerator.enum_commands(ctx)
    for enumerator in universal_ui_command_enumerator_reg:
        command_list += enumerator.enum_commands(ctx)
    return command_list


@mark.service
def get_view_element_commands(
        view_element_ui_command_reg,
        view_element_ui_command_enumerator_reg,
        ctx,
        view,
        ):
    view_t = deduce_t(view.piece)
    command_list = view_element_ui_command_reg(view_t)
    for enumerator in view_element_ui_command_enumerator_reg(view_t):
        command_list += enumerator.enum_commands(ctx)
    return command_list
