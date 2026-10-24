from . import htypes
from .code.target.import_target import ImportAliasTarget, ProjectImportsTarget
from .code.target.project import ProjectTarget
from .code.target.state import deps_state


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
        # Project imports target has only the first imports, not ones following incomplete imports.
        self._import_alias_tgt = ImportAliasTarget.ensure(targets, path)
        self._import_deps = set()

    def __repr__(self):
        return f"<Target:{self._name}>"

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        return deps_state(self.deps)

    @property
    def deps(self):
        return {
            self._project_imports_tgt,
            self._import_alias_tgt,
            *(dep.target for dep in self._import_deps),
            }

    def add_import_req(self, req):
        self._import_deps.add(req.resolve(self._targets))

    # Import job collects test functions from any module; only tests use them.
    def add_test_function(self, function):
        pass

    @property
    def result(self):
        name_to_pyobj = {}
        name_to_raw = {}
        for dep in self._import_deps:
            imports = dep.make_import()
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
