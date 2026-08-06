import logging

from .code.transport import Connection, PacketRoute

log = logging.getLogger(__name__)


class IncomingConnection(Connection):

    def __init__(self, selectors, transport, name, connection, on_eof=None):
        super().__init__(transport)
        self._selectors = selectors
        self._name = name
        self._connection = connection
        self._on_eof = on_eof

    def __str__(self):
        return f"Subprocess {self._name!r}"

    def fileno(self):
        return self._connection.fileno()

    def process(self):
        try:
            data = self._connection.recv()
        except EOFError:
            log.info("Subprocess incoming connection %r is closed by remote peer", self._name)
            self._selectors.unregister(self)
            if self._on_eof:
                self._on_eof()
            return
        self._process_data(data)


class SubprocessRoute(PacketRoute):

    def __init__(self, bundler, name, connection):
        super().__init__(bundler)
        self._name = name
        self._connection = connection

    def __str__(self):
        return f"Subprocess {self._name!r}"

    def _send_packet(self, data):
        try:
            self._connection.send(data)
        except OSError as x:
            if str(x) == 'handle is closed':
                raise RuntimeError(f"Error sending message to subprocess {self._name!r}: subprocess is gone") from x
            else:
                raise
