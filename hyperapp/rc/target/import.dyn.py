import logging
from dataclasses import dataclass

from . import htypes
from .services import (
    mosaic,
    )
from .code.boot_service_req import boot_service_cfg_items
from .code.import_dep import UnresolvedImportError, import_deps_error
from .code.import_recorder import import_recorder_piece, recorded_python_module
from .code.target.state import TargetState
from .code.type_req import type_cfg_items

log = logging.getLogger(__name__)


# Raised by a module target for import requirements it can not take.
class ImportRequirementsError(Exception):
    pass


class ProjectImportsTarget:

    @classmethod
    def ensure(cls, targets, project_name):
        name = f'imports/{project_name}'
        try:
            return targets[name]
        except KeyError:
            pass
        tgt = cls(targets, name, project_name)
        targets[name] = tgt
        return tgt

    def __init__(self, targets, name, project_name):
        self._targets = targets
        self._name = name
        self._project_name = project_name
        self._modules = []
        self._classified = False

    def __repr__(self):
        return f"<Target:{self._name}>"

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        return self._targets.deps_state(self.deps)

    @property
    def deps(self):
        return {module.import_tgt for module in self._modules}

    def add_module(self, module):
        self._modules.append(module)

    def import_finished(self):
        if self._classified:
            return
        # A failed attempt is terminal too, but fail-fast dependency state is not enough:
        # other first attempts may still supply role-defining imports.
        if not all(tgt.state in {TargetState.RESOLVED, TargetState.FAILED} for tgt in self.deps):
            return
        self._classified = True
        self._targets.classify_modules(self._modules)

    @property
    def error(self):
        return None

    @property
    def result(self):
        return None


@dataclass(frozen=True)
class _ImportResult:
    requirements: tuple
    test_functions: tuple | None  # None for an incomplete attempt.


class ImportTarget:

    @classmethod
    def ensure(cls, targets, module, idx=0):
        path = module.path
        name = f'import/{path.project}/{"/".join(path.path)}/{idx}'
        try:
            return targets[name]
        except KeyError:
            pass
        tgt = cls(targets, name, idx, module)
        targets[name] = tgt
        ImportAliasTarget.ensure(targets, path).set_import_tgt(tgt)
        return tgt

    def __init__(self, targets, name, idx, module):
        self._targets = targets
        self._name = name
        self._idx = idx
        self._module = module
        self._path = module.path
        self._source = module.source
        self._import_deps = set()
        # Job lifecycle only; RUNNABLE, and FAILED by failed deps, are derived from deps in the state property.
        self._state = TargetState.WAITING
        self._error = None
        self._first_result = None

    def __repr__(self):
        return f"<Target:{self._name}>"

    @property
    def name(self):
        return self._name

    @property
    def module(self):
        return self._module

    @property
    def module_tgt(self):
        return self._module.module_tgt

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
        return {dep.target for dep in self._import_deps}

    def add_import_dep(self, dep):
        # Deps added after the job is started would not be waited for.
        assert self._state == TargetState.WAITING, (self, self._state)
        self._import_deps.add(dep)

    # Used only when runnable or later, so all dep targets are resolved and have results.
    @property
    def _cfg_items(self):
        return self._with_loaded_cfg_items(dep.make_cfg_item() for dep in self._import_deps)

    def _with_loaded_cfg_items(self, cfg_items):
        return sorted_cfg_items([*loaded_cfg_items(self._targets, self._path), *cfg_items])

    @property
    def job(self):
        return htypes.import_job.import_job(
            target=self._name,
            path=self._path.piece,
            source=self._source,
            cfg_items=tuple(mosaic.put(item) for item in self._cfg_items),
            )

    # Module as the job imports it, or with other imports resolved, if cfg items are given.
    def recorded_module(self, cfg_items=None):
        if cfg_items is None:
            cfg_items = self._cfg_items
        else:
            cfg_items = self._with_loaded_cfg_items(cfg_items)
        recorder_piece = import_recorder_piece(self._path.piece, cfg_items)
        return recorded_python_module(self._path.path[-1], self._source, recorder_piece)

    def job_started(self):
        self._state = TargetState.RUNNING

    def job_failed(self, error, traceback=()):
        self._state = TargetState.FAILED
        self._error = error
        self._first_result = None
        log.error("%s: %s%s", self, error, ''.join(['\n', *traceback]) if traceback else '')
        if self._idx == 0:
            self._module.project_imports_tgt.import_finished()

    def _import_attempt_finished(self, requirements):
        try:
            self.module_tgt.import_attempt_finished(self._idx, requirements)
        except ImportRequirementsError as x:
            self.job_failed(str(x))
            return False
        return True

    def process_succeeded_job_result(self, requirements, test_functions):
        self._receive_result(_ImportResult(tuple(requirements), test_functions))

    def process_incomplete_job_result(self, requirements):
        self._receive_result(_ImportResult(tuple(requirements), None))

    def _receive_result(self, result):
        if self.module_tgt is None:
            assert self._idx == 0
            # Later first results can still determine this module's role.
            self._first_result = result
            self._module.first_requirements = result.requirements
            self._state = TargetState.RESOLVED
            self._module.project_imports_tgt.import_finished()
        else:
            self._process_result(result)

    def finish_classification(self):
        result = self._first_result
        self._first_result = None
        try:
            self._process_result(result)
        except Exception as x:
            # A deferred failure belongs to this attempt, not the last result that opened the barrier.
            self.job_failed(str(x))

    def _process_result(self, result):
        requirements = result.requirements
        if not self._import_attempt_finished(requirements):
            return
        if result.test_functions is None:
            self._retry(requirements)
            return
        for req in requirements:
            self.module_tgt.add_import_req(req)
        for function in result.test_functions:
            self.module_tgt.add_test_function(function)
        self._state = TargetState.RESOLVED

    def _retry(self, requirements):
        deps = {req.resolve(self._targets) for req in requirements}
        if deps <= self._import_deps:
            # Next job would get the same imports resolved and be incomplete the same way, forever.
            # Failed, so its module is not resolved without imports.
            self.job_failed("Import is incomplete, but has no new imports to resolve")
            return
        self._state = TargetState.RESOLVED
        next_tgt = ImportTarget.ensure(self._targets, self._module, idx=self._idx + 1)
        for dep in deps:
            next_tgt.add_import_dep(dep)

    @property
    def error(self):
        return self._error or import_deps_error(self._import_deps)

    @property
    def result(self):
        return None


# Preloaded resources, seen by a module and given to its import recorders up front: types and boot services.
def loaded_cfg_items(targets, path):
    return [*type_cfg_items(targets, path), *boot_service_cfg_items(targets)]


# Deps set order depends on target ids; sorted for stable pieces.
# Preloaded ones are given both up front and by deps of ones used, so duplicates are dropped.
def sorted_cfg_items(cfg_items):
    ref_to_item = {mosaic.put(item): item for item in cfg_items}
    return [item for ref, item in sorted(ref_to_item.items(), key=lambda rec: rec[0].hash)]


# Follows the last import target of a module: a next one is added while the import is incomplete.
# Resolved when the module is imported completely, to the module as that last import job imported it.
class ImportAliasTarget:

    @classmethod
    def ensure(cls, targets, path):
        name = f'import/{path.project}/{"/".join(path.path)}'
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
        self._import_tgt = None

    def __repr__(self):
        return f"<Target:{self._name}>"

    @property
    def name(self):
        return self._name

    # Has no job, so runnable or running import target is just waiting for it.
    @property
    def state(self):
        return self._targets.deps_state(self.deps)

    @property
    def deps(self):
        if self.module_tgt is None:
            return {self._import_tgt, self.module.project_imports_tgt}
        return {self._import_tgt}

    def set_import_tgt(self, tgt):
        self._import_tgt = tgt

    @property
    def module(self):
        return self._import_tgt.module

    @property
    def module_tgt(self):
        return self._import_tgt.module_tgt

    @property
    def error(self):
        return None

    @property
    def result(self):
        return self._import_tgt.recorded_module()

    # Used for tested modules, recorded with their imports resolved as a test module needs.
    def recorded_module(self, cfg_items):
        return self._import_tgt.recorded_module(cfg_items)


def resolve_requirements(requirement_creg, requirement_refs, desc="requirement"):
    requirements = [
        requirement_creg.invite(req)
        for req in requirement_refs
        ]
    for req in requirements:
        log.info("\t%s: %s", desc, req)
    return requirements


def succeeded_result(piece, request, requirement_creg, job_pool):
    target = job_pool.job_finished(piece.target)
    log.info("%s: import succeeded: %s", target, piece)
    requirements = resolve_requirements(requirement_creg, piece.requirements)
    try:
        target.process_succeeded_job_result(requirements, piece.test_functions)
    except UnresolvedImportError as x:
        target.job_failed(str(x))


def incomplete_result(piece, request, requirement_creg, job_pool):
    target = job_pool.job_finished(piece.target)
    log.info("%s: import is incomplete: %s", target, piece)
    requirements = resolve_requirements(requirement_creg, piece.requirements)
    try:
        target.process_incomplete_job_result(requirements)
    except UnresolvedImportError as x:
        target.job_failed(str(x))


def failed_result(piece, request, job_pool):
    target = job_pool.job_finished(piece.target)
    log.info("%s: import failed: %s", target, piece)
    target.job_failed(f"Import failed: {piece.error}", piece.traceback)


def internal_error_result(piece, request, job_pool):
    target = job_pool.job_finished(piece.target)
    target.job_failed(f"Import job error: {piece.error}", piece.traceback)
