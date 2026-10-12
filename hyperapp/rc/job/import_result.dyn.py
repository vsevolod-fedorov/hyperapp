import logging
from contextlib import contextmanager

from .code.path import Path

log = logging.getLogger(__name__)


_collector = None


class _ResultCollector:

    def __init__(self, stop_signal, paths):
        self._stop_signal = stop_signal
        self._pending = set(paths)
        self._path_to_error = {}

    @property
    def pending(self):
        return self._pending

    @property
    def path_to_error(self):
        return self._path_to_error

    def add(self, path, error):
        self._pending.discard(path)
        self._path_to_error[path] = error
        if not self._pending:
            self._stop_signal.fire()


@contextmanager
def collecting_import_results(stop_signal, paths):
    global _collector
    _collector = _ResultCollector(stop_signal, paths)
    try:
        yield _collector
    finally:
        _collector = None


def succeeded_result(piece, request, requirement_creg):
    path = Path.from_piece(piece.path)
    log.info("%s: import succeeded: %s", path, piece)
    requirements = [
        requirement_creg.invite(req)
        for req in piece.requirements
        ]
    for req in requirements:
        log.info("%s: requirement: %s", path, req)
    _collector.add(piece.path, None)


def failed_result(piece, request):
    path = Path.from_piece(piece.path)
    log.info("%s: import failed: %s", path, piece)
    _collector.add(piece.path, piece.error)
