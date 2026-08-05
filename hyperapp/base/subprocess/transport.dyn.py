from .code.transport import Connection, PacketRoute


class IncomingConnection(Connection):

    def __init__(self, transport, name, connection):
        super().__init__(transport)
        self._name = name
        self._connection = connection

    def __str__(self):
        return f"Subprocess {self._name!r}"

    def fileno(self):
        return self._connection.fileno()

    def process(self):
        data = self._connection.recv()
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
