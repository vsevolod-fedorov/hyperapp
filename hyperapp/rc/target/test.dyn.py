from .code.target.import_target import ImportAliasTarget
from .code.target.state import deps_state


# Test module gives no resources; it keeps imports resolved by its last import target,
# and adds a target per test function.
class TestModuleTarget:

    @classmethod
    def ensure(cls, targets, path):
        name = f'module/test/{path.project}/{"/".join(path.path)}'
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
            self._import_alias_tgt,
            *(dep.target for dep in self._import_deps),
            }

    def add_import_req(self, req):
        self._import_deps.add(req.resolve(self._targets))

    def add_test_function(self, function):
        TestTarget.ensure(self._targets, self._path, function, self)

    @property
    def result(self):
        return None


# Test function of a test module. Resolved when the test module is.
class TestTarget:

    @classmethod
    def ensure(cls, targets, path, function, module_tgt):
        name = f'test/{path.project}/{"/".join(path.path)}/{function.name}'
        try:
            return targets[name]
        except KeyError:
            pass
        tgt = cls(name, function, module_tgt)
        targets[name] = tgt
        return tgt

    def __init__(self, name, function, module_tgt):
        self._name = name
        self._function = function  # import_job.test_function piece.
        self._module_tgt = module_tgt

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
        return {self._module_tgt}

    @property
    def result(self):
        return None
