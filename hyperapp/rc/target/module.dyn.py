from . import htypes
from .code.target.import_target import ProjectImportsTarget
from .code.target.project import ProjectTarget


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
        project_tgt = ProjectTarget.ensure(targets, path.project)
        project_tgt.add_resource_tgt(path, tgt)
        return tgt

    def __init__(self, targets, name, path, source):
        self._targets = targets
        self._name = name
        self._path = path
        self._source = source
        self._project_imports_tgt = ProjectImportsTarget.ensure(targets, path.project)
        self._import_req_to_target = {}

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
        return {self._project_imports_tgt, *self._import_req_to_target.values()}

    def add_import_req(self, req):
        self._import_req_to_target[req] = req.get_target(self._targets)

    @property
    def result(self):
        name_to_pyobj = {}
        name_to_raw = {}
        for req in self._import_req_to_target:
            imports = req.resolve_to_import(self._targets)
            name_to_pyobj.update({rec.full_name: rec for rec in imports.pyobj})
            name_to_raw.update({rec.full_name: rec for rec in imports.raw})
        return htypes.builtin.python_module(
            module_name=self._path.path[-1],
            source=self._source,
            imports=htypes.builtin.imports(
                pyobj=tuple(rec for name, rec in sorted(name_to_pyobj.items())),
                raw=tuple(rec for name, rec in sorted(name_to_raw.items())),
                ),
            )
