from . import htypes
from .code.target.import_target import ProjectImportsTarget


class CompiledModuleTarget:

    @classmethod
    def ensure(cls, targets, path, source):
        name = f'module/compiled/{path.project}/{"/".join(path.path)}'
        try:
            return targets[name]
        except KeyError:
            pass
        tgt = cls(targets, name, path, source)
        targets[name] = tgt
        return tgt

    def __init__(self, targets, name, path, source):
        self._targets = targets
        self._name = name
        self._path = path
        self._source = source
        self._project_imports_tgt = ProjectImportsTarget.ensure(targets, path.project)
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
        return all(tgt.resolved for tgt in self.deps)

    @property
    def deps(self):
        return {self._project_imports_tgt, *self._deps}

    def add_dep(self, tgt):
        self._deps.add(tgt)

    @property
    def resource(self):
        return htypes.builtin.python_module(
            module_name=self._path.path[-1],
            source=self._source,
            imports=htypes.builtin.imports(
                pyobj=(),
                raw=(),
                ),
            )
