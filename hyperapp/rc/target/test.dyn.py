import logging
import traceback
from graphlib import CycleError, TopologicalSorter

from . import htypes
from .services import (
    mosaic,
    )
from .code.code_req import TestedCodeReq
from .code.import_dep import ModuleImportDep, UnresolvedImportError, import_deps_error
from .code.target.import_target import (
    ImportAliasTarget,
    ImportRequirementsError,
    loaded_cfg_items,
    resolve_requirements,
    sorted_cfg_items,
    )
from .code.target.state import TargetState

log = logging.getLogger(__name__)


# Test module gives no resources; it keeps imports resolved by its last import target,
# and adds a target per test function.
# Its first import declares all subjects. Only local compiled subjects wait for these tests.
class TestModuleTarget:

    def __init__(self, targets, path, source):
        self._targets = targets
        self._name = f'module/test/{path.project}/{"/".join(path.path)}'
        self._path = path
        self._source = source
        self._import_alias_tgt = ImportAliasTarget.ensure(targets, path)
        self._import_deps = set()
        self._tested_import_deps = set()
        self._recorded_subjects = {}  # Local provider Path -> import alias. Foreign subjects are complete modules.
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
        if self.error or self.blocked_by_tested_imports:
            return TargetState.FAILED
        return self._targets.deps_state(self.deps)

    @property
    def import_deps(self):
        return self._import_deps

    # Local recorded providers would cycle through their tests if we waited for their completed modules.
    @property
    def deps(self):
        return {self._import_alias_tgt, *self.deps_for_imports(self._import_deps)}

    # Import retries execute tested code too, so they need the same resolved dependencies as tests.
    def deps_for_imports(self, import_deps):
        return {
            *(dep.target for dep in import_deps),
            *(self._provider_import_alias(dep) or dep.target for dep in self._tested_module_import_deps),
            }

    # For compiled modules it tests to wait for. Test functions are known when this target is resolved.
    @property
    def test_deps(self):
        return {self, *self._test_alias_tgts}

    @property
    def _tested_modules(self):
        return {dep.module for dep in self._tested_import_deps}

    @property
    def recorded_paths(self):
        return self._recorded_subjects.keys()

    @property
    def _tested_module_import_deps(self):
        return {
            dep
            for alias_tgt in self._recorded_subjects.values()
            for dep in alias_tgt.module_tgt.import_deps
            }

    # A provider is a different importer: its ordinary import of another subject gets that recorded module.
    def _provider_import_alias(self, dep):
        if isinstance(dep, ModuleImportDep):
            return self._recorded_subjects.get(dep.module.path)
        return None

    def import_attempt_finished(self, idx, requirements):
        req_to_dep = {
            req: req.resolve(self._targets) for req in requirements if isinstance(req, TestedCodeReq)
            }
        if idx == 0:
            self._tested_import_deps = set(req_to_dep.values())
            for dep in self._tested_import_deps:
                if (alias_tgt := dep.recorded_alias) is not None:
                    self._recorded_subjects[dep.module.path] = alias_tgt
                    alias_tgt.module_tgt.add_test_module(self)
            return
        new_tested = [req for req, dep in req_to_dep.items() if dep.module not in self._tested_modules]
        if new_tested:
            raise ImportRequirementsError(
                f"Tested modules are imported by import attempt #{idx} only:"
                f" {', '.join(sorted('.'.join(req.import_as) for req in new_tested))}. Tested modules are decided"
                " by the first attempt; import them before anything making the test module import incomplete")

    # Tested modules and their imports are decided by imports; executing tested code cannot extend them.
    # Preloaded ones, like types, are not: they are given to all recorders, see add_tested_loaded_reqs.
    def check_test_requirements(self, requirements, tested_requirements):
        # A cached test module need not repeat its module-level imports. Check against those
        # declarations without adding a test function's observations to its siblings' jobs.
        self._targets.code_imports.check(requirements)
        for req in requirements:
            if not isinstance(req, TestedCodeReq):
                continue
            dep = req.resolve(self._targets)
            if dep.module not in self._tested_modules:
                *package, name = dep.import_path
                raise ImportRequirementsError(
                    f"This test uses {dep.module.path}, but {self._path} did not declare it as a test subject."
                    f" Add `from .{'.'.join(package)} import {name}` at module level.")
        self.check_provider_requirements(tested_requirements, when='test runs')

    def check_provider_requirements(self, tested_requirements, when):
        self._targets.code_imports.check(tested_requirements)
        for req in tested_requirements:
            provider = self._recorded_provider(req.path)
            if not req.is_preloaded and req.resolve(self._targets) not in provider.import_deps:
                raise ImportRequirementsError(
                    f"Tested module {req.path} uses {'.'.join(req.import_as)} when the {when},"
                    " but not when it is imported, so it is not resolved for tests")

    def _recorded_provider(self, path):
        try:
            return self._recorded_subjects[path].module_tgt
        except KeyError:
            raise UnresolvedImportError(f"{self._path}: Unexpected requirement for unrecorded subject {path}")

    # Import retries and tests can call functions whose types and boot services were not used at import time.
    # They are resolved from the start, so taking them does not change what tested modules wait for.
    # Taken from successful jobs only: an incomplete one is retried in full.
    def add_tested_loaded_reqs(self, tested_requirements):
        for req in tested_requirements:
            if req.is_preloaded:
                self._recorded_provider(req.path).add_import_req(req)

    def add_import_req(self, req):
        self._import_deps.add(req.resolve(self._targets))

    def add_test_function(self, function):
        TestTarget.ensure(self._targets, self, function)
        self._test_alias_tgts.add(TestAliasTarget.ensure(self._targets, self._path, function.name))

    # Direct imports of a recorded subject must refer to the same module the test gets.
    # Imports through a completed module use that module's published dependencies.
    @property
    def cfg_items(self):
        return [*loaded_cfg_items(self._targets, self._path), *(self.make_cfg_item(dep) for dep in self._import_deps)]

    def make_cfg_item(self, dep):
        alias_tgt = dep.recorded_alias if isinstance(dep, ModuleImportDep) else None
        return self._cfg_item(dep, alias_tgt)

    def _cfg_item(self, dep, alias_tgt):
        if alias_tgt is None:
            return dep.make_cfg_item()
        return htypes.import_recorder.import_cfg_item(
            import_path=dep.import_path,
            resource=mosaic.put(self._recorded_module(alias_tgt)),
            )

    def _recorded_module(self, alias_tgt):
        cfg_items = sorted_cfg_items(
            self._cfg_item(dep, self._provider_import_alias(dep)) for dep in alias_tgt.module_tgt.import_deps)
        return alias_tgt.recorded_module(cfg_items)

    # Hint for a dependency cycle going through this target, as target list, first one repeated last:
    # it is a tested module imported by another tested one through an untested one. None if it is not.
    def cycle_hint(self, cycle):
        untested_tgt = cycle[cycle.index(self) + 1]  # Self is never only last: it is repeated first.
        tested_module_tgts = {alias_tgt.module_tgt for alias_tgt in self._recorded_subjects.values()}
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
        return import_deps_error(self._import_deps | self._tested_import_deps)

    @property
    def blocked_by_tested_imports(self):
        # The aliases bypass completed providers, but their recorded pieces still need a finite
        # chain of resource refs. Leave diagnostics for bad imports and cycles on the providers.
        imports = TopologicalSorter()
        for alias in self._recorded_subjects.values():
            for dep in alias.module_tgt.import_deps:
                if dep.error:
                    return True
                if other := self._provider_import_alias(dep):
                    imports.add(alias, other)
        try:
            imports.prepare()
        except CycleError:
            return True
        return False

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
        targets.add(path.project, tgt)
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
        if self.error:
            return TargetState.FAILED
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
            *(self._module_tgt.make_cfg_item(dep) for dep in self._import_deps),
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

    def _check_requirements(self, requirements, tested_requirements):
        try:
            self._module_tgt.check_test_requirements(requirements, tested_requirements)
        except (ImportRequirementsError, UnresolvedImportError) as x:
            self.job_failed(str(x))
            return False
        return True

    def process_succeeded_job_result(self, requirements, tested_requirements, constructor_refs, rc_constructor_creg):
        # Reading a recorder without forcing its value does not interrupt the test.
        if not self._check_requirements(requirements, tested_requirements):
            return
        pending = self._targets.constructors.prepare(
            rc_constructor_creg, constructor_refs, self._module_tgt.recorded_paths, source_target=self._name)
        self._module_tgt.add_tested_loaded_reqs(tested_requirements)
        self._targets.constructors.apply(pending)
        self._state = TargetState.RESOLVED

    def process_incomplete_job_result(self, requirements, tested_requirements):
        if not self._check_requirements(requirements, tested_requirements):
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
        return self._error or import_deps_error(self._import_deps)

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
        targets.add(path.project, tgt)
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


# Of tested requirements of a succeeded test, only preloaded ones, like types, are added to module resources.
def succeeded_result(piece, request, requirement_creg, rc_constructor_creg, job_pool):
    target = job_pool.job_finished(piece.target)
    log.info("%s: test succeeded: %s", target, piece)
    try:
        requirements = resolve_requirements(requirement_creg, piece.requirements)
        tested_requirements = resolve_requirements(requirement_creg, piece.tested_requirements, "tested module requirement")
        target.process_succeeded_job_result(requirements, tested_requirements, piece.constructors, rc_constructor_creg)
    except Exception as x:
        # Empty str(x), as with AssertionError(), would be omitted from CompileResult.errors.
        target.job_failed(''.join(traceback.format_exception_only(x)).strip())


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
