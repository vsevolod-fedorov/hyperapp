from .code.target.state import TargetState


# Boot service, a loaded builtin one: it is not compiled, so it is resolved from the start.
class BootServiceTarget:

    @classmethod
    def ensure(cls, targets, service_name, piece):
        name = f'boot_service/{service_name}'
        try:
            return targets[name]
        except KeyError:
            pass
        tgt = cls(name, piece)
        targets[name] = tgt
        return tgt

    def __init__(self, name, piece):
        self._name = name
        self._piece = piece

    def __repr__(self):
        return f"<Target:{self._name}>"

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        return TargetState.RESOLVED

    @property
    def deps(self):
        return set()

    @property
    def error(self):
        return None

    @property
    def result(self):
        return self._piece
