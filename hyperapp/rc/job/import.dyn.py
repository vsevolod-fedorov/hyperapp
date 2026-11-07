import inspect
import logging
import traceback

from . import htypes
from .services import (
    mosaic,
    pyobj_creg,
    web,
    )
from .code.context import ActiveModule, job_active, tested_modules
from .code.ctr_collector import constructor_snapshot, find_collection_error
from .code.path import Path
from .code.import_recorder import (
    enum_import_requirements,
    find_incomplete_error,
    import_recorder_piece,
    recorded_python_module,
    recorded_python_module_name,
    register_import_recorder_pyobj,
    )
from .code.probe import real_fn

log = logging.getLogger(__name__)


def run_import_job(piece, request, import_to_req, marker_registry, subsystem_factory, transport):
    log.info("[%s] Run import job: %s", request, piece)
    path = Path.from_piece(piece.path)
    register_import_recorder_pyobj()
    cfg_items = [web.summon(ref) for ref in piece.cfg_items]
    recorder_piece = import_recorder_piece(piece.path, cfg_items)
    recorder = pyobj_creg.animate(recorder_piece)
    modules, tested_recorders = tested_modules(cfg_items)
    # Tested uses belong to this job, not earlier imports or tests on this worker.
    for tested_path, rec in tested_recorders:
        rec.clear_used_imports()
    module_piece = recorded_python_module(piece.path.path[-1], piece.source, recorder_piece)
    module_name = recorded_python_module_name(module_piece)
    modules[module_name] = ActiveModule(path, mosaic.put(module_piece))
    test_functions = ()
    constructors = ()
    error = None
    try:
        with job_active(subsystem_factory, marker_registry, modules) as context:
            try:
                module = pyobj_creg.animate(module_piece)
                log.info("Imported module: %s", module)
                test_functions = tuple(_enum_test_functions(module))
            except Exception as x:
                if collection_error := find_collection_error(x):
                    raise collection_error
                error = x
            else:
                # Snapshot while the sink and services are alive; cleanup can still reject it.
                constructors = constructor_snapshot(context)
        # Outside the execution handler, so requirement errors are not chained to the import error.
        requirements = tuple(enum_import_requirements(path, recorder, import_to_req))
        tested_requirements = tuple(
            req
            for path, rec in tested_recorders
            for req in enum_import_requirements(path, rec, import_to_req)
            )
    except Exception as x:
        log.exception("Import job error")
        result = htypes.import_job.internal_error_result(
            target=piece.target,
            error=str(x),
            traceback=tuple(traceback.format_tb(x.__traceback__)),
            )
    else:
        result = _import_result(piece, requirements, tested_requirements, test_functions, constructors, error)
    transport.send_message(request.remote_peer, request.local_identity, result)


def _import_result(piece, requirements, tested_requirements, test_functions, constructors, error):
    if error is None:
        return htypes.import_job.succeeded_result(
            target=piece.target,
            requirements=requirements,
            tested_requirements=tested_requirements,
            test_functions=test_functions,
            constructors=constructors,
            )
    if (incomplete := find_incomplete_error(error)) is not None:
        log.info("Import is incomplete: %s", incomplete)
        return htypes.import_job.incomplete_result(
            target=piece.target,
            requirements=requirements,
            tested_requirements=tested_requirements,
            )
    log.info("Import failed: %s", error)
    return htypes.import_job.failed_result(
        target=piece.target,
        requirements=requirements,
        error=str(error),
        traceback=tuple(traceback.format_tb(error.__traceback__)),
        )


# Collected from any module: job does not know if it is a test one.
def _enum_test_functions(module):
    for name, value in vars(module).items():
        if not name.startswith('test_'):
            continue
        fn = real_fn(value)
        if not inspect.isfunction(fn):
            continue
        if fn.__module__ != module.__name__:
            continue  # Imported from other module.
        is_async_gen = inspect.isasyncgenfunction(fn)
        yield htypes.test_job.test_function(
            name=name,
            params=tuple(inspect.signature(fn).parameters),
            is_async=inspect.iscoroutinefunction(fn) or is_async_gen,
            is_generator=inspect.isgeneratorfunction(fn) or is_async_gen,
            )
