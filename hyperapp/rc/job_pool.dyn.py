import logging
from contextlib import contextmanager

log = logging.getLogger(__name__)


class JobPool:

    class _Pool:

        def __init__(self, transport, identity, stop_signal, workers):
            self._transport = transport
            self._identity = identity
            self._stop_signal = stop_signal
            self._free_workers = [*workers.peers]
            self._queue = []
            self._pending = {}  # target name -> (target, peer)
            self._completed = []

        @property
        def pending(self):
            return self._pending or self._queue

        @property
        def completed(self):
            return self._completed

        def start_job(self, target):
            # Mark queued jobs as started too, so the target is not runnable anymore and won't be queued twice.
            target.job_started()
            if not self._free_workers:
                self._queue.append(target)
                return
            self._send_job(target)

        def _send_job(self, target):
            peer = self._free_workers.pop(0)
            log.info("Start job for: %s at %s", target.name, peer)
            self._transport.send_message(peer, self._identity, target.job)
            self._pending[target.name] = (target, peer)

        def job_finished(self, target_name):
            target, peer = self._pending.pop(target_name)
            self._completed.append(target)
            self._free_workers.append(peer)
            if self._queue:
                self._send_job(self._queue.pop(0))
            if not self.pending:
                self._stop_signal.fire()
            return target

    def __init__(self, transport):
        self._transport = transport
        self._instance = None

    @contextmanager
    def running(self, identity, stop_signal, workers):
        self._instance = self._Pool(self._transport, identity, stop_signal, workers)
        try:
            yield
        finally:
            self._instance = None

    @property
    def pending(self):
        return self._instance.pending

    @property
    def completed(self):
        return self._instance.completed

    def start_job(self, target):
        self._instance.start_job(target)

    def job_finished(self, target_name):
        return self._instance.job_finished(target_name)


def job_pool(transport):
    return JobPool(transport)
