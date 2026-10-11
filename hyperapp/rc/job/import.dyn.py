import logging
import traceback

from . import htypes
from .services import (
    mosaic,
    pyobj_creg,
    )
from .code.system import setup_system
from .code.import_recorder import register_import_recorder_pyobj
from .data.base.config import config as base_config

log = logging.getLogger(__name__)


def run_import_job(piece, request, transport):
    log.info("[%s] Run import job: %s", request, piece)
    register_import_recorder_pyobj()
    service_creg = setup_system([base_config])
    recorder_piece = htypes.import_recorder.import_recorder(
        module_path=piece.path,
        )
    recorder = pyobj_creg.animate(recorder_piece)
    python_module = htypes.builtin.python_module(
        module_name=piece.path.path[-1],
        source=piece.source,
        imports=htypes.builtin.imports(
            pyobj=(
                htypes.builtin.import_rec(
                    full_name='',
                    resource=mosaic.put(recorder_piece),
                    ),
                ),
            raw=(),
            ),
        )
    try:
        module = pyobj_creg.animate(python_module)
        log.info("Imported module: %s", module)
        result = htypes.import_job.succeeded_result(
            path=piece.path,
            used_imports=tuple(recorder.used_imports),
            )
    except Exception as x:
        log.info("Import failed: %s", x)
        result = htypes.import_job.failed_result(
            path=piece.path,
            used_imports=tuple(recorder.used_imports),
            error=str(x),
            traceback=tuple(traceback.format_tb(x.__traceback__)),
            )
    transport.send_message(request.remote_peer, request.local_identity, result)
