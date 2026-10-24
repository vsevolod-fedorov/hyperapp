from . import htypes
from .code.code_req import TestedCodeReq
from .code.target.import_target import ImportAliasTarget, ImportRequirementsError, ProjectImportsTarget
from .code.target.project import ProjectTarget
from .code.target.state import TargetState, deps_state
from .code.target.test import TestModuleTarget


# Made for each dyn module: code imports are resolved to it before its first import decides if it is
# a compiled or a test module. Added to targets and its project only when it is decided to be compiled.
class CompiledModuleTarget:

    def __init__(self, targets, path, source):
        self._targets = targets
        self._name = f'module/compiled/{path.project}/{"/".join(path.path)}'
        self._path = path
        self._source = source
        self._project_imports_tgt = ProjectImportsTarget.ensure(targets, path.project)
        # Project imports target has only the first imports, not ones following incomplete imports.
        self._import_alias_tgt = ImportAliasTarget.ensure(targets, path)
        self._import_deps = set()
        self._is_test = False
        # Test modules testing this one. Added by their first imports, so all are known
        # when the project imports target is resolved.
        self._test_module_tgts = set()

    def __repr__(self):
        return f"<Target:{self._name}>"

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        if self._is_test:
            return TargetState.FAILED  # Test module is imported as code.
        return deps_state(self.deps)

    @property
    def deps(self):
        return {
            self._project_imports_tgt,
            self._import_alias_tgt,
            *(dep.target for dep in self._import_deps),
            *(tgt for test_module_tgt in self._test_module_tgts for tgt in test_module_tgt.test_deps),
            }

    @property
    def import_deps(self):
        return self._import_deps

    # Returns target for the module to use from now on.
    # Module having tested code imports is a test module, giving no resources.
    # Decided by the first import attempt, which the project imports target waits for.
    def import_attempt_finished(self, idx, requirements):
        tested = [req for req in requirements if isinstance(req, TestedCodeReq)]
        if idx == 0:
            if tested:
                self._is_test = True
                test_module_tgt = TestModuleTarget.ensure(self._targets, self._path, self._source)
                return test_module_tgt.import_attempt_finished(idx, requirements)
            self._targets[self._name] = self
            ProjectTarget.ensure(self._targets, self._path.project).add_resource_tgt(self._path, self)
            return self
        if tested:
            raise ImportRequirementsError(
                f"Tested modules are imported by import attempt #{idx} only:"
                f" {', '.join('.'.join(req.import_as) for req in tested)}. Whether a module is a test one"
                " is decided by the first attempt; import them before anything making the import incomplete")
        return self

    def add_test_module(self, test_module_tgt):
        self._test_module_tgts.add(test_module_tgt)

    def add_import_req(self, req):
        self._import_deps.add(req.resolve(self._targets))

    # Import job collects test functions from any module; only tests use them.
    def add_test_function(self, function):
        pass

    @property
    def error(self):
        return None

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
