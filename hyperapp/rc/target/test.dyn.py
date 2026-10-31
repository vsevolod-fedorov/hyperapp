import logging

from . import htypes
from .services import (
    mosaic,
    )
from .code.code_req import TestedCodeReq
from .code.import_dep import UnresolvedImportError
from .code.type_req import TypeReq, type_cfg_items
from .code.target.import_target import (
    ImportAliasTarget,
    ImportRequirementsError,
    resolve_requirements,
    sorted_cfg_items,
    )
from .code.target.state import TargetState

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
        return self._targets.deps_state(self.deps)

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

    # None for other imports, and for tested manual modules: these are tested as they are, like code imports,
    # and having no resources to give, do not wait for tests.
    def _req_tested_alias_tgt(self, req):
        if not isinstance(req, TestedCodeReq):
            return None
        tgt = req.resolve(self._targets).target
        if isinstance(tgt, ImportAliasTarget):
            return tgt
        return None

    # Returns target for the module to use from now on: self.
    def import_attempt_finished(self, idx, requirements):
        req_to_alias_tgt = {
            req: alias_tgt
            for req in requirements
            if (alias_tgt := self._req_tested_alias_tgt(req)) is not None
            }
        if idx == 0:
            self._tested_alias_tgts = set(req_to_alias_tgt.values())
            for alias_tgt in self._tested_alias_tgts:
                alias_tgt.module_tgt.add_test_module(self)
            return self
        new_tested = [req for req, alias_tgt in req_to_alias_tgt.items() if alias_tgt not in self._tested_alias_tgts]
        if new_tested:
            raise ImportRequirementsError(
                f"Tested modules are imported by import attempt #{idx} only:"
                f" {', '.join(sorted('.'.join(req.import_as) for req in new_tested))}. Tested modules are decided"
                " by the first attempt; import them before anything making the test module import incomplete")
        return self

    # Tested modules and their imports are decided by imports, so a test run discovering others is an error.
    # Types are not: they are given to all recorders, see add_tested_types.
    def check_test_requirements(self, requirements, tested_requirements):
        for req in requirements:
            alias_tgt = self._req_tested_alias_tgt(req)
            if alias_tgt is not None and alias_tgt not in self._tested_alias_tgts:
                return (
                    f"Tested module {'.'.join(req.import_as)} is first used when the test runs."
                    " Tested modules are decided by the test module import; import it at module level")
        for req in tested_requirements:
            if isinstance(req, TypeReq):
                continue
            alias_tgt = ImportAliasTarget.ensure(self._targets, req.path)
            if req.resolve(self._targets) not in alias_tgt.module_tgt.import_deps:
                return (
                    f"Tested module {req.path} uses {'.'.join(req.import_as)} when the test runs,"
                    " but not when it is imported, so it is not resolved for tests")
        return None

    # Types used by tested modules only in functions are found only by test runs, which call them.
    # Types are resolved from the start, so taking them does not change what tested modules wait for.
    # Taken from passed runs only: next run after an incomplete one runs the whole test again.
    def add_tested_types(self, tested_requirements):
        for req in tested_requirements:
            if isinstance(req, TypeReq):
                ImportAliasTarget.ensure(self._targets, req.path).module_tgt.add_import_req(req)

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
        return [*type_cfg_items(self._targets, self._path), *(self._cfg_item(dep) for dep in self._import_deps)]

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

    # Hint for a dependency cycle going through this target, as target list, first one repeated last:
    # it is a tested module imported by another tested one through an untested one. None if it is not.
    def cycle_hint(self, cycle):
        untested_tgt = cycle[cycle.index(self) + 1]  # Self is never only last: it is repeated first.
        tested_module_tgts = {alias_tgt.module_tgt for alias_tgt in self._tested_alias_tgts}
        if untested_tgt in tested_module_tgts:
            return None
        importers = sorted(
            (tgt for tgt in tested_module_tgts if any(dep.target is untested_tgt for dep in tgt.import_deps)),
            key=lambda tgt: tgt.name)
        tested_in_cycle = [tgt for tgt in cycle if tgt in tested_module_tgts]
        if not importers or not tested_in_cycle:
            return None
        tested, importer, untested = tested_in_cycle[0].path, importers[0].path, untested_tgt.path
        return (
            f"Tested module {tested} is imported by tested module {importer} through untested module {untested}."
            f" Being complete, {untested} requires complete {tested}, which waits for its tests."
            " Tested modules may import each other only directly")

    @property
    def error(self):
        return None

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
        self._error = None
        if function.params:
            self.job_failed(f"Fixtures are not supported yet; test has params: {', '.join(function.params)}")

    def __repr__(self):
        return f"<Target:{self._name}>"

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        if self._state == TargetState.WAITING:
            state = self._targets.deps_state(self.deps)
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

    def job_failed(self, error, traceback=()):
        self._state = TargetState.FAILED
        self._error = error
        log.error("%s: %s%s", self, error, ''.join(['\n', *traceback]) if traceback else '')

    def process_succeeded_job_result(self, tested_requirements):
        self._module_tgt.add_tested_types(tested_requirements)
        self._state = TargetState.RESOLVED

    def process_incomplete_job_result(self, requirements, tested_requirements):
        if error := self._module_tgt.check_test_requirements(requirements, tested_requirements):
            self.job_failed(error)
            return
        deps = {req.resolve(self._targets) for req in requirements}
        if deps <= self._all_import_deps:
            # Next job would be incomplete the same way, forever.
            self.job_failed("Test is incomplete, but has no new imports to resolve")
            return
        self._state = TargetState.RESOLVED
        next_tgt = TestTarget.ensure(self._targets, self._module_tgt, self._function, idx=self._idx + 1)
        for dep in deps:
            next_tgt.add_import_dep(dep)

    @property
    def error(self):
        return self._error

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
        tgt = cls(targets, name)
        targets[name] = tgt
        return tgt

    def __init__(self, targets, name):
        self._targets = targets
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
        return self._targets.deps_state(self.deps)

    @property
    def deps(self):
        return {self._test_tgt}

    def set_test_tgt(self, tgt):
        self._test_tgt = tgt

    @property
    def error(self):
        return None

    @property
    def result(self):
        return None


# Of tested requirements of a succeeded test, only types are added to module resources.
def succeeded_result(piece, request, requirement_creg, job_pool):
    target = job_pool.job_finished(piece.target)
    log.info("%s: test succeeded: %s", target, piece)
    tested_requirements = resolve_requirements(requirement_creg, piece.tested_requirements, "tested module requirement")
    try:
        target.process_succeeded_job_result(tested_requirements)
    except UnresolvedImportError as x:
        target.job_failed(str(x))


def incomplete_result(piece, request, requirement_creg, job_pool):
    target = job_pool.job_finished(piece.target)
    log.info("%s: test is incomplete: %s", target, piece)
    requirements = resolve_requirements(requirement_creg, piece.requirements)
    tested_requirements = resolve_requirements(requirement_creg, piece.tested_requirements, "tested module requirement")
    try:
        target.process_incomplete_job_result(requirements, tested_requirements)
    except UnresolvedImportError as x:
        target.job_failed(str(x))


def failed_result(piece, request, job_pool):
    target = job_pool.job_finished(piece.target)
    target.job_failed(f"Test failed: {piece.error}", piece.traceback)


def internal_error_result(piece, request, job_pool):
    target = job_pool.job_finished(piece.target)
    target.job_failed(f"Test job error: {piece.error}", piece.traceback)
