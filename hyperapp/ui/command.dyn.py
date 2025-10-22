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


class Command:

    def __init__(self, view_reg, visualizer, command_creg, key, name, command, ctx):
        self._view_reg = view_reg
        self._visualizer = visualizer
        self._command_creg = command_creg
        self._key = key
        self._name = name
        self._command = command
        self._ctx = ctx

    @property
    def key(self):
        return self._key

    @property
    def name(self):
        return self._name

    def start(self):
        log.info("Start command: %r", self._name)
        asyncio.create_task(self.run())

    async def run(self):
        try:
            result = self._command_creg.animate(self._command, self._ctx)
            if inspect.iscoroutine(result):
                result = await result
        except Exception as x:
            await self._handle_error(x)
            return
        if result is None:
            return
        result = self._prepare_result(result)
        model = web.summon_opt(result.model)
        key = web.summon_opt(result.key)
        if result.diff:
            self._process_diff(result.diff)
        await self._open(model, key)

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

    async def _open(self, model, key):
        if model is None and key is None:
            return
        if model is None:
            log.info("Command %r: Set current key: %r", self._name, key)
            navigator = self._ctx.navigator.view
            navigator.set_current_key(self._navigator_widget, key)
            return

        try:
            view_piece = await self._visualizer(self._ctx, real_model_t(model))
        except Exception as x:
            await self._handle_error(x)
            return
        model_ctx = self._ctx.pop().clone_with(model=model)
        await self._open_view(model, model_ctx, view_piece, key)

    async def _open_view(self, model, model_ctx, view_piece, key=None):
        view = self._view_reg.animate(view_piece, model_ctx)
        log.info("Command %r: visualizing with view: %s", self._name, view)
        navigator = self._ctx.navigator.view
        await navigator.open(self._ctx, model, view, self._navigator_widget, key=key)

    @property
    def _navigator_widget(self):
        w = self._ctx.navigator.widget_wr()
        if w is None:
            raise RuntimeError("Navigator widget is gone")
        return w


@mark.service
def command_factory(view_reg, visualizer, command_creg, key, name, command, ctx):
    return Command(view_reg, visualizer, command_creg, key, name, command, ctx)


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
