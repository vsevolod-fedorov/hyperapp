import logging
import logging.handlers
import traceback
import threading
from contextlib import contextmanager
from enum import Enum

from hyperapp.common import cdr_coders  # self-registering
from hyperapp.common.services import Services

log = logging.getLogger(__name__)


# Note: copy shared with subprocess_connection.dyn.py
class ConnectionEvent(Enum):
    STOP = 1
    EXCEPTION = 2
    PARCEL = 3


def log_traceback(traceback_entries):
    for entry in traceback_entries:
        for line in entry.splitlines():
            log.error("%s", line.rstrip())


def subprocess_main(process_name, connection, type_module_list, code_module_list, config):
    with logging_inited(process_name):
        try:
            subprocess_main_safe(connection, type_module_list, code_module_list, config)
            connection.send((ConnectionEvent.STOP.value, None))
        except Exception as x:
            log.error("Exception in subprocess: %s", x)
            traceback_entries = traceback.format_tb(x.__traceback__)
            log_traceback(traceback_entries)
            # Traceback is not pickleable, convert it to string list.
            connection.send((ConnectionEvent.EXCEPTION.value, (x, traceback_entries)))


@contextmanager
def logging_inited(process_name):
    format = '%(asctime)s.%(msecs)03d %(name)-46s %(lineno)4d %(threadName)10s %(levelname)-8s  %(message)s'
    datefmt = '%M:%S'
    handler = logging.FileHandler(f'/tmp/{process_name}.log', mode='w')
    handler.setFormatter(logging.Formatter(format, datefmt))

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(handler)

    try:
        yield
    finally:
        handler.close()


def subprocess_main_safe(connection, type_module_list, code_module_list, config):
    services = Services()
    services.master_process_connection = connection
    services.subprocess_stop_event = threading.Event()
    services.init_services()
    services.init_modules(type_module_list, code_module_list, config)
    services.start()
    log.info("Running, waiting for stop signal.")
    services.subprocess_stop_event.wait()
    services.stop()
