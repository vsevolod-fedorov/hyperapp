import logging

from . import htypes
from .services import (
    mosaic,
    )
from .code.import_dep import UnresolvedImportError
from .code.import_recorder import import_recorder_piece, recorded_python_module
from .code.target.state import TargetState

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
        self._deps = set()

    def __repr__(self):
        return f"<Target:{self._name}>"

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        return self._targets.deps_state(self._deps)

    @property
    def deps(self):
        return self._deps

    def add_dep(self, tgt):
        self._deps.add(tgt)

    @property
    def error(self):
        return None

    @property
    def result(self):
        return None


class ImportTarget:

    @classmethod
    def ensure(cls, targets, path, source, module_tgt, idx=0):
        name = f'import/{path.project}/{"/".join(path.path)}/{idx}'
        try:
            return targets[name]
        except KeyError:
            pass
        tgt = cls(targets, name, idx, path, source, module_tgt)
        targets[name] = tgt
        ImportAliasTarget.ensure(targets, path).set_import_tgt(tgt)
        return tgt

    def __init__(self, targets, name, idx, path, source, module_tgt):
        self._targets = targets
        self._name = name
        self._idx = idx
        self._path = path
        self._source = source
        self._module_tgt = module_tgt
        self._import_deps = set()
        # Job lifecycle only; RUNNABLE, and FAILED by failed deps, are derived from deps in the state property.
        self._state = TargetState.WAITING
        self._error = None

    def __repr__(self):
        return f"<Target:{self._name}>"

    @property
    def name(self):
        return self._name

    @property
    def module_tgt(self):
        return self._module_tgt

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
        return {dep.target for dep in self._import_deps}

    def add_import_dep(self, dep):
        # Deps added after the job is started would not be waited for.
        assert self._state == TargetState.WAITING, (self, self._state)
        self._import_deps.add(dep)

    # Used only when runnable or later, so all dep targets are resolved and have results.
    @property
    def _cfg_items(self):
        return sorted_cfg_items(dep.make_cfg_item() for dep in self._import_deps)

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
        recorder_piece = import_recorder_piece(self._path.piece, cfg_items)
        return recorded_python_module(self._path.path[-1], self._source, recorder_piece)

    def job_started(self):
        self._state = TargetState.RUNNING

    def job_failed(self, error, traceback=()):
        self._state = TargetState.FAILED
        self._error = error
        log.error("%s: %s%s", self, error, ''.join(['\n', *traceback]) if traceback else '')

    def _import_attempt_finished(self, requirements):
        try:
            self._module_tgt = self._module_tgt.import_attempt_finished(self._idx, requirements)
        except ImportRequirementsError as x:
            self.job_failed(str(x))
            return False
        return True

    def process_succeeded_job_result(self, requirements, test_functions):
        if not self._import_attempt_finished(requirements):
            return
        self._state = TargetState.RESOLVED
        for req in requirements:
            self._module_tgt.add_import_req(req)
        for function in test_functions:
            self._module_tgt.add_test_function(function)

    def process_incomplete_job_result(self, requirements):
        if not self._import_attempt_finished(requirements):
            return
        deps = {req.resolve(self._targets) for req in requirements}
        if deps <= self._import_deps:
            # Next job would get the same imports resolved and be incomplete the same way, forever.
            # Failed, so its module is not resolved without imports.
            self.job_failed("Import is incomplete, but has no new imports to resolve")
            return
        self._state = TargetState.RESOLVED
        next_tgt = ImportTarget.ensure(self._targets, self._path, self._source, self._module_tgt, idx=self._idx + 1)
        for dep in deps:
            next_tgt.add_import_dep(dep)

    @property
    def error(self):
        return self._error

    @property
    def result(self):
        return None


# Deps set order depends on target ids; sorted for stable pieces.
def sorted_cfg_items(cfg_items):
    return sorted(cfg_items, key=lambda item: mosaic.put(item).hash)


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
        return {self._import_tgt}

    def set_import_tgt(self, tgt):
        self._import_tgt = tgt

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
