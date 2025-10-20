# Model commands wrapped to UI commands
# or UI commands returning model wrapped to UI commands.

import logging
from collections import namedtuple
from functools import cached_property
from operator import attrgetter, itemgetter

from . import htypes
from .services import (
    deduce_t,
    pyobj_creg,
    mosaic,
    web,
    )
from .code.mark import mark
from .code.remote_model import real_model_t

log = logging.getLogger(__name__)


def split_command_result(result):
    if type(result) is tuple and len(result) == 2:
        model, key = result
    elif isinstance(result, htypes.command.command_result):
        model = web.summon_opt(result.model)
        key = web.summon_opt(result.key)
    else:
        model = result
        key = None
    if type(model) is list:
        model = tuple(model)
    return (model, key)
