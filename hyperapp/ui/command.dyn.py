import asyncio
import inspect
import logging

from . import htypes
from .services import (
    mosaic,
    web,
    )
from .code.mark import mark
from .code.remote_model import real_model_t

log = logging.getLogger(__name__)


class CommandRunner:

    def __init__(self, view_reg, visualizer, command_creg):
        self._view_reg = view_reg
        self._visualizer = visualizer
        self._command_creg = command_creg

    async def run_command(self, ctx, command):
        command_ctx = prepare_command_ctx(ctx)
        try:
            result = await self.run_model_command(command_ctx, command)
        except Exception as x:
            await self._handle_error(x)
            return
        if result is None:
            return None
        result = self._prepare_result(result)
        model = web.summon_opt(result.model)
        key = web.summon_opt(result.key)
        if result.diff:
            self._process_diff(result.diff)
        await self._open(command, ctx, model, key)

    async def run_model_command(self, command_ctx, command):
        result = self._command_creg.animate(command, command_ctx)
        if inspect.iscoroutine(result):
            result = await result
        return result

    @staticmethod
    def _prepare_result(result):
        if isinstance(result, htypes.command.command_result):
            return result
        if result is None:
            return result
        if type(result) is tuple and len(result) == 2:
            model, key = result
        else:
            model = result
            key = None
        if type(model) is list:
            model = tuple(model)
        return htypes.command.command_result(
            model=mosaic.put_opt(model),
            key=mosaic.put_opt(key),
            diff=None,
            )

    async def _handle_error(self, exception):
        raise  # TODO

    def _process_diff(self, model_diff_ref):
        assert 0, exception  # TODO

    async def _open(self, command, ctx, model, key):
        if model is None and key is None:
            return
        if model is None:
            log.info("%s: Set current key: %r", command, key)
            navigator = ctx.navigator.view
            navigator.set_current_key(self._navigator_widget(ctx), key)
            return
        try:
            view_piece = await self._visualizer(ctx, real_model_t(model))
        except Exception as x:
            await self._handle_error(x)
            return
        model_ctx = ctx.pop().clone_with(model=model)
        await self._open_view(ctx, model, model_ctx, view_piece, key)

    async def _open_view(self, ctx, model, model_ctx, view_piece, key=None):
        view = self._view_reg.animate(view_piece, model_ctx)
        log.info("Visualizing %s with view: %s", model, view)
        navigator = ctx.navigator.view
        await navigator.open(ctx, model, view, self._navigator_widget(ctx), key=key)

    def _navigator_widget(self, ctx):
        w = ctx.navigator.widget_wr()
        if w is None:
            raise RuntimeError("Navigator widget is gone")
        return w


class Command:

    def __init__(self, command_runner, ctx, key, name, command):
        self._runner = command_runner
        self._ctx = ctx
        self._key = key
        self._name = name
        self._command = command

    def __repr__(self):
        return f"<Command {self._name!r}, key={self.key}>"

    def __str__(self):
        return f"command {self._name!r}"

    @property
    def key(self):
        return self._key

    @property
    def name(self):
        return self._name

    @property
    def command(self):
        return self._command

    @property
    def ctx(self):
        return self._ctx

    def start(self):
        log.info("Start command: %r", self._name)
        asyncio.create_task(self.run())

    async def run(self):
        await self._runner.run_command(self._ctx, self._command)


def prepare_command_ctx(ctx):
    kw = {}
    if 'model_state' in ctx:
        kw.update(ctx.attributes(ctx.model_state))
    if 'widget' in ctx:
        widget = ctx.widget()
        if widget is None:
            raise RuntimeError("Widget is gone")
        kw['widget'] = widget  # Replace weakref with actual widget.
        if 'view' in ctx:
            kw['state'] = ctx.view.widget_state(widget)
    if 'input' in ctx and 'value' not in ctx:
        kw['value'] = ctx.input.get_value()
    return ctx.push(**kw)


@mark.service
def command_runner(view_reg, visualizer, command_creg):
    return CommandRunner(view_reg, visualizer, command_creg)


@mark.service
def command_factory(command_runner, key, name, command, ctx):
    return Command(command_runner, ctx, key, name, command)


def _amend_fragment(text):
    if text.endswith('...'):
        suffix = '...'
        text = text.removesuffix('...')
    else:
        suffix = ''
    text = text.split('.')[-1]
    text = text.removesuffix('()')
    text = text.removesuffix('_d')
    text = text.replace('_', ' ')
    text = text.capitalize()
    return text + suffix


def command_d_text(format, d):
    text = format(d)
    fragments = text.split(': ')
    amended_fragments = [_amend_fragment(f) for f in fragments]
    return ": ".join(amended_fragments)


def command_text(format, command):
    return command_d_text(format, command.d)
