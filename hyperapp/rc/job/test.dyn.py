import asyncio
import logging
import traceback

from . import htypes
from .services import (
    pyobj_creg,
    web,
    )
from .code.context import job_active, tested_modules
from .code.ctr_collector import constructor_snapshot, find_collection_error
from .code.path import Path
from .code.import_recorder import (
    enum_import_requirements,
    find_incomplete_error,
    import_recorder_piece,
    recorded_python_module,
    register_import_recorder_pyobj,
    )

log = logging.getLogger(__name__)


def run_test_job(piece, request, import_to_req, marker_registry, subsystem_factory, transport):
    log.info("[%s] Run test job: %s", request, piece)
    path = Path.from_piece(piece.path)
    register_import_recorder_pyobj()
    cfg_items = [web.summon(ref) for ref in piece.cfg_items]
    recorder_piece = import_recorder_piece(piece.path, cfg_items)
    recorder = pyobj_creg.animate(recorder_piece)
    modules, tested_recorders = tested_modules(cfg_items)
    # Recorders are cached by their pieces, so this worker may have given them to its previous jobs.
    # Their uses must not be reported as this job's: a test run is failed by unexpected ones.
    for rec in [recorder, *(rec for path, rec in tested_recorders)]:
        rec.clear_used_imports()
    module_piece = recorded_python_module(piece.path.path[-1], piece.source, recorder_piece)
    # Tested modules are active while their tests run. The test module itself is deliberately absent:
    # its own import job already performed its marker discoveries.
    constructors = ()
    error = None
    try:
        with job_active(subsystem_factory, marker_registry, modules) as context:
            try:
                module = pyobj_creg.animate(module_piece)
                _run_test_fn(getattr(module, piece.function.name), piece.function)
            except Exception as x:
                if collection_error := find_collection_error(x):
                    raise collection_error
                error = x
            else:
                # Async functions and generators have finished completely before this snapshot.
                constructors = constructor_snapshot(context)
        # Outside the execution handler, so requirement errors are not chained to the test error.
        requirements = tuple(enum_import_requirements(path, recorder, import_to_req))
        tested_requirements = tuple(
            req
            for path, rec in tested_recorders
            for req in enum_import_requirements(path, rec, import_to_req)
            )
    except Exception as x:
        log.exception("Test job error")
        result = htypes.test_job.internal_error_result(
            target=piece.target,
            error=str(x),
            traceback=tuple(traceback.format_tb(x.__traceback__)),
            )
    else:
        result = _test_result(piece, requirements, tested_requirements, constructors, error)
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


def _test_result(piece, requirements, tested_requirements, constructors, error):
    if error is None:
        return htypes.test_job.succeeded_result(
            target=piece.target,
            tested_requirements=tested_requirements,
            constructors=constructors,
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
