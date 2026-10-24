import logging

from . import htypes
from .services import (
    mosaic,
    )
from .code.code_req import TestedCodeReq
from .code.target.import_target import ImportAliasTarget, resolve_requirements, sorted_cfg_items
from .code.target.state import TargetState, deps_state

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
        self._test_alias_tgts = set()

    def __repr__(self):
        return f"<Target:{self._name}>"

    @property
    def name(self):
        return self._name

    @property
    def path(self):
        return self._path

    @property
    def source(self):
        return self._source

    @property
    def state(self):
        return deps_state(self.deps)

    @property
    def import_deps(self):
        return self._import_deps

    # Tested modules are waited for by their import aliases: complete ones wait for tests.
    # Other modules imported by tested ones are complete, compiled before tests.
    @property
    def deps(self):
        tested_imports = (dep for alias_tgt in self._tested_alias_tgts for dep in alias_tgt.module_tgt.import_deps)
        return {
            self._import_alias_tgt,
            *(self._dep_target(dep) for dep in self._import_deps),
            *(self._dep_target(dep) for dep in tested_imports),
            }

    # For compiled modules it tests to wait for. Test functions are known when this target is resolved.
    @property
    def test_deps(self):
        return {self, *self._test_alias_tgts}

    def _tested_alias_tgt(self, dep):
        if dep.target in self._tested_alias_tgts:
            return dep.target  # Tested code import.
        for alias_tgt in self._tested_alias_tgts:
            if dep.target is alias_tgt.module_tgt:
                return alias_tgt  # Code import of a tested module.
        return None

    def _dep_target(self, dep):
        return self._tested_alias_tgt(dep) or dep.target

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

    # Tested modules and their imports are decided by imports, so a test run discovering others is an error.
    def check_test_requirements(self, requirements, tested_requirements):
        for req in requirements:
            if not isinstance(req, TestedCodeReq):
                continue
            if req.resolve(self._targets).target not in self._tested_alias_tgts:
                return (
                    f"Tested module {'.'.join(req.import_as)} is first used when the test runs."
                    " Tested modules are decided by the test module import; import it at module level")
        for req in tested_requirements:
            alias_tgt = ImportAliasTarget.ensure(self._targets, req.path)
            if req.resolve(self._targets) not in alias_tgt.module_tgt.import_deps:
                return (
                    f"Tested module {req.path} uses {'.'.join(req.import_as)} when the test runs,"
                    " but not when it is imported, so it is not resolved for tests")
        return None

    def add_import_req(self, req):
        self._import_deps.add(req.resolve(self._targets))

    def add_test_function(self, function):
        TestTarget.ensure(self._targets, self, function)
        self._test_alias_tgts.add(TestAliasTarget.ensure(self._targets, self._path, function.name))

    # Tested modules are recorded, and so are their direct imports of other tested modules: these are
    # the same recorded modules the test gets. Imports through untested modules are got by complete modules,
    # which can not import recorded ones.
    @property
    def cfg_items(self):
        return [self._cfg_item(dep) for dep in self._import_deps]

    def _cfg_item(self, dep):
        alias_tgt = self._tested_alias_tgt(dep)
        if alias_tgt is None:
            return dep.make_cfg_item()
        return htypes.import_recorder.import_cfg_item(
            import_path=dep.import_path,
            resource=mosaic.put(self._recorded_module(alias_tgt)),
            )

    def _recorded_module(self, alias_tgt):
        cfg_items = sorted_cfg_items(self._cfg_item(dep) for dep in alias_tgt.module_tgt.import_deps)
        return alias_tgt.recorded_module(cfg_items)

    @property
    def result(self):
        return None


# Test function of a test module, run when the test module imports are resolved.
# When the test run is incomplete, a next target is added with the new imports resolved.
class TestTarget:

    @classmethod
    def ensure(cls, targets, module_tgt, function, idx=0):
        path = module_tgt.path
        name = f'test/{path.project}/{"/".join(path.path)}/{function.name}/{idx}'
        try:
            return targets[name]
        except KeyError:
            pass
        tgt = cls(targets, name, idx, module_tgt, function)
        targets[name] = tgt
        TestAliasTarget.ensure(targets, path, function.name).set_test_tgt(tgt)
        return tgt

    def __init__(self, targets, name, idx, module_tgt, function):
        self._targets = targets
        self._name = name
        self._idx = idx
        self._module_tgt = module_tgt
        self._function = function  # test_job.test_function piece.
        self._import_deps = set()  # Ones added by incomplete runs; test module ones are kept by its target.
        # Job lifecycle only; RUNNABLE, and FAILED by failed deps, are derived from deps in the state property.
        self._state = TargetState.WAITING
        if function.params:
            log.error("%s: Fixtures are not supported yet; test has params: %s", self, ", ".join(function.params))
            self._state = TargetState.FAILED

    def __repr__(self):
        return f"<Target:{self._name}>"

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        if self._state == TargetState.WAITING:
            state = deps_state(self.deps)
            if state == TargetState.RESOLVED:
                return TargetState.RUNNABLE
            return state
        return self._state

    @property
    def deps(self):
        return {
            self._module_tgt,
            *(dep.target for dep in self._import_deps),
            }

    @property
    def _all_import_deps(self):
        return self._module_tgt.import_deps | self._import_deps

    def add_import_dep(self, dep):
        # Deps added after the job is started would not be waited for.
        assert self._state == TargetState.WAITING, (self, self._state)
        self._import_deps.add(dep)

    # Job is produced only when runnable, so all dep targets are resolved and have results.
    @property
    def job(self):
        path = self._module_tgt.path
        cfg_items = sorted_cfg_items([
            *self._module_tgt.cfg_items,
            *(dep.make_cfg_item() for dep in self._import_deps),
            ])
        return htypes.test_job.test_job(
            target=self._name,
            path=path.piece,
            source=self._module_tgt.source,
            cfg_items=tuple(mosaic.put(item) for item in cfg_items),
            function=self._function,
            )

    def job_started(self):
        self._state = TargetState.RUNNING

    def job_failed(self):
        self._state = TargetState.FAILED

    def process_succeeded_job_result(self):
        self._state = TargetState.RESOLVED

    def process_incomplete_job_result(self, requirements, tested_requirements):
        if error := self._module_tgt.check_test_requirements(requirements, tested_requirements):
            log.error("%s: %s", self, error)
            self.job_failed()
            return
        deps = {req.resolve(self._targets) for req in requirements}
        if deps <= self._all_import_deps:
            # Next job would be incomplete the same way, forever.
            log.error("%s: test is incomplete, but has no new imports to resolve", self)
            self.job_failed()
            return
        self._state = TargetState.RESOLVED
        next_tgt = TestTarget.ensure(self._targets, self._module_tgt, self._function, idx=self._idx + 1)
        for dep in deps:
            next_tgt.add_import_dep(dep)

    @property
    def result(self):
        return None


# Follows the last run of a test function: a next one is added while the run is incomplete.
# Resolved when the test is passed, failed when it is failed.
class TestAliasTarget:

    @classmethod
    def ensure(cls, targets, path, fn_name):
        name = f'test/{path.project}/{"/".join(path.path)}/{fn_name}'
        try:
            return targets[name]
        except KeyError:
            pass
        tgt = cls(name)
        targets[name] = tgt
        return tgt

    def __init__(self, name):
        self._name = name
        self._test_tgt = None

    def __repr__(self):
        return f"<Target:{self._name}>"

    @property
    def name(self):
        return self._name

    # Has no job, so runnable or running test target is just waiting for it.
    @property
    def state(self):
        return deps_state(self.deps)

    @property
    def deps(self):
        return {self._test_tgt}

    def set_test_tgt(self, tgt):
        self._test_tgt = tgt

    @property
    def result(self):
        return None


# Tested requirements of a succeeded test are not used yet: they are not added to module resources.
def succeeded_result(piece, request, requirement_creg, job_pool):
    target = job_pool.job_finished(piece.target)
    log.info("%s: test succeeded: %s", target, piece)
    resolve_requirements(requirement_creg, piece.tested_requirements, "tested module requirement")
    target.process_succeeded_job_result()


def incomplete_result(piece, request, requirement_creg, job_pool):
    target = job_pool.job_finished(piece.target)
    log.info("%s: test is incomplete: %s", target, piece)
    requirements = resolve_requirements(requirement_creg, piece.requirements)
    tested_requirements = resolve_requirements(requirement_creg, piece.tested_requirements, "tested module requirement")
    target.process_incomplete_job_result(requirements, tested_requirements)


def failed_result(piece, request, job_pool):
    target = job_pool.job_finished(piece.target)
    log.error("%s: test failed: %s\n%s", target, piece.error, ''.join(piece.traceback))
    target.job_failed()


def internal_error_result(piece, request, job_pool):
    target = job_pool.job_finished(piece.target)
    log.error("%s: test job error: %s\n%s", target, piece.error, ''.join(piece.traceback))
    target.job_failed()
