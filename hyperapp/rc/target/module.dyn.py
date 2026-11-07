from . import htypes
from .code.code_req import TestedCodeReq
from .code.import_dep import import_deps_error
from .code.target.import_target import ImportAliasTarget, ImportRequirementsError, ProjectImportsTarget
from .code.target.state import TargetState


# Created only after the project imports barrier identifies a resource-producing module.
class CompiledModuleTarget:

    def __init__(self, targets, module):
        path = module.path
        self._targets = targets
        self._name = f'module/compiled/{path.project}/{"/".join(path.path)}'
        self._path = path
        self._source = module.source
        self._project_imports_tgt = ProjectImportsTarget.ensure(targets, path.project)
        # Project imports target has only the first imports, not ones following incomplete imports.
        self._import_alias_tgt = ImportAliasTarget.ensure(targets, path)
        self._import_deps = set()
        # Test modules testing this one. Added by their first imports, so all are known
        # when the project imports target is resolved.
        self._test_module_tgts = module.test_module_tgts

    def __repr__(self):
        return f"<Target:{self._name}>"

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        if self.error:
            return TargetState.FAILED
        return self._targets.deps_state(self.deps)

    @property
    def deps(self):
        return {
            self._project_imports_tgt,
            self._import_alias_tgt,
            *(dep.target for dep in self._import_deps),
            *(tgt for test_module_tgt in self._test_module_tgts for tgt in test_module_tgt.test_deps),
            }

    @property
    def path(self):
        return self._path

    @property
    def import_deps(self):
        return self._import_deps

    # Classification uses first attempts only; later imports cannot turn this module into a test.
    def import_attempt_finished(self, idx, requirements):
        tested = [req for req in requirements if isinstance(req, TestedCodeReq)]
        if tested:
            raise ImportRequirementsError(
                f"Tested modules are imported by import attempt #{idx} only:"
                f" {', '.join('.'.join(req.import_as) for req in tested)}. Whether a module is a test one"
                " is decided by the first attempt; import them before anything making the import incomplete")

    @property
    def constructors(self):
        return self._targets.constructors.for_path(self._path)

    def add_import_req(self, req):
        self._import_deps.add(req.resolve(self._targets))

    # Import job collects test functions from any module; only tests use them.
    def add_test_function(self, function):
        pass

    @property
    def error(self):
        return import_deps_error(self._import_deps)

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


# Module having hand-written resources: not compiled, so it is resolved from the start.
# Code imports of it are resolved to its loaded module resource.
class ManualModuleTarget:

    def __init__(self, path, piece):
        self._name = f'module/manual/{path.project}/{"/".join(path.path)}'
        self._path = path
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
    def path(self):
        return self._path

    @property
    def error(self):
        return None

    @property
    def result(self):
        return self._piece
