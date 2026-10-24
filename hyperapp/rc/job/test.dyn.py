import asyncio
import logging
import traceback

from . import htypes
from .services import (
    pyobj_creg,
    web,
    )
from .code.system import setup_system
from .code.path import Path
from .code.import_recorder import (
    enum_import_requirements,
    find_incomplete_error,
    import_recorder_piece,
    module_recorder_piece,
    recorded_python_module,
    register_import_recorder_pyobj,
    )
from .data.base.config import config as base_config

log = logging.getLogger(__name__)


def run_test_job(piece, request, import_to_req, transport):
    log.info("[%s] Run test job: %s", request, piece)
    path = Path.from_piece(piece.path)
    register_import_recorder_pyobj()
    service_creg = setup_system([base_config])
    cfg_items = [web.summon(ref) for ref in piece.cfg_items]
    recorder_piece = import_recorder_piece(piece.path, cfg_items)
    recorder = pyobj_creg.animate(recorder_piece)
    tested_recorders = list(_tested_recorders(cfg_items))
    # Recorders are cached by their pieces, so this worker may have given them to its previous jobs.
    # Their uses must not be reported as this job's: a test run is failed by unexpected ones.
    for rec in [recorder, *(rec for path, rec in tested_recorders)]:
        rec.clear_used_imports()
    try:
        module = pyobj_creg.animate(recorded_python_module(piece.path.path[-1], piece.source, recorder_piece))
        _run_test_fn(getattr(module, piece.function.name), piece.function)
        error = None
    except Exception as x:
        error = x
    # Collected outside of the except block, so its errors are not chained to the test error.
    try:
        requirements = tuple(enum_import_requirements(path, recorder, import_to_req))
        tested_requirements = tuple(
            req
            for path, rec in tested_recorders
            for req in enum_import_requirements(path, rec, import_to_req)
            )
    except Exception as x:
        log.exception("Error collecting requirements")
        result = htypes.test_job.internal_error_result(
            target=piece.target,
            error=str(x),
            traceback=tuple(traceback.format_tb(x.__traceback__)),
            )
    else:
        result = _test_result(piece, requirements, tested_requirements, error)
    transport.send_message(request.remote_peer, request.local_identity, result)


def _run_test_fn(fn, function):
    if function.is_async:
        asyncio.run(_run_async_test_fn(fn, function))
    elif function.is_generator:
        for _ in fn():
            pass
    else:
        fn()


async def _run_async_test_fn(fn, function):
    if function.is_generator:
        async for _ in fn():
            pass
    else:
        await fn()


# Tested modules are imported recorded, so their recorders keep what they use while the test runs.
# Yields (tested module path, its recorder).
def _tested_recorders(cfg_items):
    for item in cfg_items:
        if not isinstance(item, htypes.import_recorder.import_cfg_item):
            continue
        recorder_piece = module_recorder_piece(web.summon(item.resource))
        if recorder_piece is None:
            continue  # Complete module, not a tested one.
        yield (Path.from_piece(recorder_piece.module_path), pyobj_creg.animate(recorder_piece))


def _test_result(piece, requirements, tested_requirements, error):
    if error is None:
        return htypes.test_job.succeeded_result(
            target=piece.target,
            tested_requirements=tested_requirements,
            )
    if (incomplete := find_incomplete_error(error)) is not None:
        log.info("Test is incomplete: %s", incomplete)
        return htypes.test_job.incomplete_result(
            target=piece.target,
            requirements=requirements,
            tested_requirements=tested_requirements,
            )
    log.info("Test failed: %s", error)
    return htypes.test_job.failed_result(
        target=piece.target,
        # Assertion errors have no message, so the exception type is included.
        error=''.join(traceback.format_exception_only(error)).strip(),
        traceback=tuple(traceback.format_tb(error.__traceback__)),
        )
