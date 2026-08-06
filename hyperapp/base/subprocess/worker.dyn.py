import itertools
import logging
import threading
from contextlib import ExitStack, contextmanager

from .code.make_partial import make_partial
from .code.futures import get_process_future
from .code.selectors import StopSignal
from .code.transport import IncomingConnection
from .data.worker_boot import boot as worker_boot

log = logging.getLogger(__name__)


_process_id_counter = itertools.count()
_process_sync = {}


class _Workers:

    def __init__(self, peers):
        self.peers = peers


class _Sync:

    def __init__(self, stop_signal, wanted_count):
        self._stop_signal = stop_signal
        self._wanted_count = wanted_count
        self._lock = threading.Lock()
        self._process_id_to_peer = {}
        self._failed_process_ids = set()

    @property
    def peers(self):
        return [
            peer for process_id, peer
            in sorted(self._process_id_to_peer.items())
            ]

    @property
    def failed_count(self):
        return len(self._failed_process_ids)

    def worker_started(self, process_id, peer):
        log.info("Worker %d is started: peer=%s", process_id, peer)
        with self._lock:
            self._process_id_to_peer[process_id] = peer
            self._check_ready()

    def worker_failed(self, process_id, exit_code):
        log.info("Worker %d is failed with exit code %d", process_id, exit_code)
        with self._lock:
            self._failed_process_ids.add(process_id)
            self._check_ready()

    @property
    def is_ready(self):
        return len(self._process_id_to_peer) + len(self._failed_process_ids) == self._wanted_count

    def _check_ready(self):
        if self.is_ready:
            self._stop_signal.fire()


class _Sentinel:

    def __init__(self, selectors, sync, process_id, process):
        self._selectors = selectors
        self._sync = sync
        self._process_id = process_id
        self._process = process
        self._registered = False

    def fileno(self):
        return self._process.sentinel

    def process(self):
        self._selectors.unregister(self)
        self._registered = False
        self._sync.worker_failed(self._process_id, self._process.exitcode)

    @contextmanager
    def registered(self):
        self._selectors.register(self)
        self._registered = True
        try:
            yield
        finally:
            if self._registered:
                self._selectors.unregister(self)


def worker_started(piece, request):
    sync = _process_sync[piece.process_id]
    sync.worker_started(piece.process_id, request.remote_peer)


def subprocess_workers_running(
        selectors,
        transport,
        subprocess_running,
        ):

    @contextmanager
    def _subprocess_workers_running(master_identity, name, count, timeout_sec, start_timeout_sec):
        with ExitStack() as stack:
            stop_signal = StopSignal()
            sync = _Sync(stop_signal, count)
            for idx in range(count):
                process_id = next(_process_id_counter)
                _process_sync[process_id] = sync
                future = get_process_future(process_id)
                main = make_partial(
                    worker_boot, process_id=process_id, master_peer=master_identity.peer.piece)
                worker_name = f'{name}-{idx:02d}'
                rec = stack.enter_context(subprocess_running(worker_name, main))
                connection = IncomingConnection(transport, worker_name, rec.connection)
                transport.register_connection(connection)
                sentinel = _Sentinel(selectors, sync, process_id, rec.process)
                stack.enter_context(sentinel.registered())
            stack.enter_context(selectors.registered(stop_signal))
            selectors.run()
            if sync.failed_count:
                raise RuntimeError(f"{sync.failed_count} workers are failed to start")
            yield _Workers(sync.peers)

    return _subprocess_workers_running
