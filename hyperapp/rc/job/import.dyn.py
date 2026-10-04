import logging

from . import htypes
from .services import (
    pyobj_creg,
    )
from .code.system import setup_system
from .data.base.config import config as base_config

log = logging.getLogger(__name__)


def run_import_job(piece, request):
    log.info("[%s] Run import job: %s", request, piece)
    service_creg = setup_system([base_config])
    python_module = htypes.builtin.python_module(
        module_name=piece.path.path[-1],
        source=piece.source,
        imports=htypes.builtin.imports(pyobj=(), raw=()),
        )
    module = pyobj_creg.animate(python_module)
    log.info("Imported module: %s", module)
