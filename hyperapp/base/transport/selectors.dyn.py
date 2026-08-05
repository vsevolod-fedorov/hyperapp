from selectors import EVENT_READ, DefaultSelector


class Selectors:

    def __init__(self):
        self._selectors = DefaultSelector()

    def register(self, obj, mask=EVENT_READ):
        self._selectors.register(obj, mask)

    def unregister(self, obj):
        self._selectors.unregister(obj)

    def run(self, timeout_sec=None):
        while True:
            for key, events in self._selectors.select(timeout_sec):
                if key.fileobj.process():
                    break


def selectors():
    return Selectors()
