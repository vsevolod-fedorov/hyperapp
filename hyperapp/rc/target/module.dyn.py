from . import htypes
from .code.target.import_target import ProjectImportsTarget
from .code.target.project import ProjectTarget
from .code.target.state import TargetState


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
        # Last import target; set by it right after this target is created.
        # Project imports target has only the first ones, not ones following incomplete imports.
        self._import_tgt = None
        self._import_req_to_path_target = {}

    def __repr__(self):
        return f"<Target:{self._name}>"

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        if all(tgt.state == TargetState.RESOLVED for tgt in self.deps):
            return TargetState.RESOLVED
        return TargetState.WAITING

    @property
    def deps(self):
        return {
            self._project_imports_tgt,
            self._import_tgt,
            *(tgt for path, tgt in self._import_req_to_path_target.values()),
            }

    def set_import_tgt(self, tgt):
        self._import_tgt = tgt

    def add_import_req(self, req):
        self._import_req_to_path_target[req] = req.find_import_target(self._targets)

    @property
    def result(self):
        name_to_pyobj = {}
        name_to_raw = {}
        for req, (import_path, tgt) in self._import_req_to_path_target.items():
            imports = req.resolve_to_import(import_path, tgt)
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
