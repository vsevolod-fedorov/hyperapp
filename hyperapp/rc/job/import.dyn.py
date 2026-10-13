import logging
import traceback

from . import htypes
from .services import (
    mosaic,
    pyobj_creg,
    )
from .code.system import setup_system
from .code.path import Path
from .code.import_recorder import register_import_recorder_pyobj
from .data.base.config import config as base_config

log = logging.getLogger(__name__)


def _without_prefixes(import_paths):
    return [
        import_path for import_path in import_paths
        if not any(
            len(other) > len(import_path) and other[:len(import_path)] == import_path
            for other in import_paths
            )
        ]


def _enum_import_requirements(path, recorder, import_to_req):
    for import_path in sorted(_without_prefixes(recorder.used_imports)):
        req = import_to_req(path, import_path)
        if req is not None:
            yield mosaic.put(req)


def run_import_job(piece, request, import_to_req, transport):
    log.info("[%s] Run import job: %s", request, piece)
    path = Path.from_piece(piece.path)
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
            target=piece.target,
            requirements=tuple(_enum_import_requirements(path, recorder, import_to_req)),
            )
    except Exception as x:
        log.info("Import failed: %s", x)
        result = htypes.import_job.failed_result(
            target=piece.target,
            requirements=tuple(_enum_import_requirements(path, recorder, import_to_req)),
            error=str(x),
            traceback=tuple(traceback.format_tb(x.__traceback__)),
            )
    transport.send_message(request.remote_peer, request.local_identity, result)
