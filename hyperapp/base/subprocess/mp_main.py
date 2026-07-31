import logging
import logging.handlers
import os
import traceback
import threading
from contextlib import contextmanager
from pathlib import Path

from hyperapp.boot.htypes import bundle_t
from hyperapp.boot.htypes.packet_coders import packet_coders
from hyperapp.boot.boot import boot_services
# from hyperapp.boot.services import HYPERAPP_DIR, Services

log = logging.getLogger(__name__)



# TODO: Use $XDG_STATE_HOME/hyperapp/subprocess/logs and rotate them.
def _logs_dir():
    runtime_dir = (
        os.environ.get('XDG_RUNTIME_DIR')
        or tempfile.gettempdir()
        )
    dir = Path(runtime_dir) / 'hyperapp/subprocess/logs'
    dir.mkdir(parents=True, exist_ok=True)
    return dir


@contextmanager
def logging_inited(process_name):
    format = '%(asctime)s.%(msecs)03d %(name)-46s %(lineno)4d %(threadName)10s %(levelname)-8s  %(message)s'
    datefmt = '%H:%M:%S'
    dir = _logs_dir()
    path = dir / f'{process_name}.log'
    handler = logging.FileHandler(path, mode='w')
    handler.setFormatter(logging.Formatter(format, datefmt))

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(handler)

    try:
        yield
    finally:
        handler.close()


def subprocess_main(process_name, connection, main_fn_bundle_cdr):
    with logging_inited(process_name):
        try:
            subprocess_main_safe(connection, main_fn_bundle_cdr)
        except Exception as x:
            log.exception("Subprocess: Failed with exception: %r", x)
        connection.close()


def subprocess_main_safe(connection, main_fn_bundle_cdr):
    log.info("Subprocess: Init services.")
    svc = boot_services()

    pyobj_creg = svc.pyobj_creg
    unbundler = svc.unbundler

    log.info("Subprocess: Unpack main function. Bundle size: %.2f KB", len(main_fn_bundle_cdr)/1024)

    bundle = packet_coders.decode('cdr', main_fn_bundle_cdr, bundle_t)
    received_refs = unbundler.register_bundle(bundle)
    main_fn_ref = bundle.roots[0]
    main_fn = pyobj_creg.invite(main_fn_ref)

    log.info("Subprocess: Run main function %s: %s", main_fn_ref, main_fn)
    main_fn(connection, received_refs)
    log.info("Subprocess: Done.")
