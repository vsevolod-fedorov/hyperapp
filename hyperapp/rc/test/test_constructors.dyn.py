from . import htypes
from .code.ctr_collector import COLLECTOR_REF
from .code.path import Path
from .code.probe import ProbeBase, real_fn
from .code.constructor import Constructor


# A concrete payload with no service inference or resource-generation policy.
class TestConstructor(Constructor):

    @classmethod
    def from_piece(cls, piece):
        return cls(Path.from_piece(piece.path), piece.key, piece.value)

    def __init__(self, path, key, value):
        super().__init__(path, key)
        self.value = value

    @property
    def piece(self):
        return htypes.test_constructors.constructor(self.path.piece, self.key, self.value)


class TestConstructorProbe(ProbeBase):

    def __call__(self, *args, **kw):
        result = self._fn(*args, **kw)
        ctr = TestConstructor(self.path, f'call:{real_fn(self).__qualname__}', str(result))
        self.context.invite(COLLECTOR_REF).add_constructor(ctr, self)
        self.state['calls'] = self.state.get('calls', 0) + 1
        return result


def constructor_marker(fn, path, collector):
    probe = TestConstructorProbe(path, fn)
    collector.declare(TestConstructor(path, f'declare:{real_fn(fn).__qualname__}', 'declared'), fn)
    return probe
