import asyncio
import inspect
import logging

from . import htypes
from .services import (
    mosaic,
    )

log = logging.getLogger(__name__)


class Command:

    def __init__(self, t, name, command, ctx):
        self.t = t
        self.name = name
        self.command = command
        self.ctx = ctx

    def start(self, command_creg):
        log.info("Start command: %r", self.name)
        asyncio.create_task(self.run(command_creg))

    async def run(self, command_creg):
        result = command_creg.animate(self.command, self.ctx)
        if inspect.iscoroutine(result):
            result = await result
        if result is None:
            return
        result = self._prepare_result(result)

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
