import logging

from .code.code_req import TestedCodeReq
from .code.target.import_target import ImportAliasTarget
from .code.target.state import deps_state

log = logging.getLogger(__name__)


# Test module gives no resources; it keeps imports resolved by its last import target,
# and adds a target per test function.
# Its first import decides which modules it tests; project imports target waits for it,
# so compiled modules know their tests before they are resolved, and wait for them.
class TestModuleTarget:

    @classmethod
    def ensure(cls, targets, path, source):
        name = f'module/test/{path.project}/{"/".join(path.path)}'
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
        self._import_alias_tgt = ImportAliasTarget.ensure(targets, path)
        self._import_deps = set()
        self._tested_alias_tgts = set()  # Import alias targets of tested modules.

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

    # For compiled modules it tests to wait for.
    @property
    def test_deps(self):
        return {self}

    # Returns self, or None if import requirements are wrong.
    def import_attempt_finished(self, idx, requirements):
        req_to_alias_tgt = {
            req: req.resolve(self._targets).target
            for req in requirements
            if isinstance(req, TestedCodeReq)
            }
        if idx == 0:
            self._tested_alias_tgts = set(req_to_alias_tgt.values())
            for alias_tgt in self._tested_alias_tgts:
                alias_tgt.module_tgt.add_test_module(self)
            return self
        new_tested = [req for req, alias_tgt in req_to_alias_tgt.items() if alias_tgt not in self._tested_alias_tgts]
        if new_tested:
            log.error(
                "%s: Tested modules are imported by import attempt #%d only: %s. Tested modules are decided by"
                " the first attempt; import them before anything making the test module import incomplete",
                self, idx, ", ".join(sorted('.'.join(req.import_as) for req in new_tested)))
            return None
        return self

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
