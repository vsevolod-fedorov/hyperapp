
class CompiledModuleTarget:

    @classmethod
    def ensure(cls, targets, path):
        name = f'module/compiled/{path.project}/{"/".join(path.path)}'
        try:
            return targets[name]
        except KeyError:
            pass
        tgt = cls(targets, name, path)
        targets[name] = tgt
        return tgt

    def __init__(self, targets, name, path):
        self._targets = targets
        self._name = name
        self._path = path
        self._deps = set()

    def __repr__(self):
        return f"<Target:{self._name}>"

    @property
    def name(self):
        return self._name

    @property
    def runnable(self):
        return False

    @property
    def resolved(self):
        return all(tgt.resolved for tgt in self._deps)

    @property
    def deps(self):
        return self._deps

    def add_dep(self, tgt):
        self._deps.add(tgt)
