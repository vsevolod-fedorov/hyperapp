import socket
from contextlib import contextmanager
from selectors import EVENT_READ, DefaultSelector


class StopSignal:

    def __init__(self):
        self._r, self._w = socket.socketpair()
        self._r.setblocking(False)

    def fire(self):
        self._w.send(b'x')

    def fileno(self):
        return self._r.fileno()

    def process(self):
        self._r.recv(1024)
        return True


class Selectors:

    def __init__(self):
        self._selectors = DefaultSelector()

    @contextmanager
    def registered(self, obj, mask=EVENT_READ):
        self.register(obj, mask)
        try:
            yield
        finally:
            self.unregister(obj)

    def register(self, obj, mask=EVENT_READ):
        self._selectors.register(obj, mask)

    def unregister(self, obj):
        self._selectors.unregister(obj)

    def run(self, timeout_sec=None):
        while True:
            ready_list = self._selectors.select(timeout_sec)
            if not ready_list:
                break  # Timed out or got signal
            for key, events in ready_list:
                if key.fileobj.process():
                    return

    def run_once(self, timeout_sec=None):
        ready_list = self._selectors.select(timeout_sec)
        for key, events in ready_list:
            key.fileobj.process()
        return bool(ready_list)


def selectors():
    return Selectors()
