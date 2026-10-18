import logging

from . import htypes
from .code.target.state import TargetState

log = logging.getLogger(__name__)


class ProjectImportsTarget:

    @classmethod
    def ensure(cls, targets, project_name):
        idx = 0
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
        if all(tgt.state == TargetState.RESOLVED for tgt in self._deps):
            return TargetState.RESOLVED
        return TargetState.WAITING

    @property
    def deps(self):
        return self._deps

    def add_dep(self, tgt):
        self._deps.add(tgt)

    @property
    def result(self):
        return None


class ImportTarget:

    @classmethod
    def ensure(cls, targets, path, source, module_tgt):
        idx = 0
        name = f'import/{path.project}/{"/".join(path.path)}/{idx}'
        try:
            return targets[name]
        except KeyError:
            pass
        tgt = cls(targets, name, idx, path, source, module_tgt)
        targets[name] = tgt
        project_imports_tgt = ProjectImportsTarget.ensure(targets, path.project)
        project_imports_tgt.add_dep(tgt)
        return tgt

    def __init__(self, targets, name, idx, path, source, module_tgt):
        self._targets = targets
        self._name = name
        self._idx = idx
        self._path = path
        self._source = source
        self._module_tgt = module_tgt
        self._state = TargetState.RUNNABLE  # No deps, so it is runnable right away.

    def __repr__(self):
        return f"<Target:{self._name}>"

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        return self._state

    @property
    def deps(self):
        return set()

    @property
    def job(self):
        return htypes.import_job.import_job(
            target=self._name,
            path=self._path.piece,
            source=self._source,
            )

    def job_started(self):
        self._state = TargetState.RUNNING

    def process_job_result(self, requirements):
        self._state = TargetState.RESOLVED
        for req in requirements:
            self._module_tgt.add_import_req(req)

    @property
    def result(self):
        return None


def succeeded_result(piece, request, requirement_creg, job_pool):
    target = job_pool.job_finished(piece.target)
    log.info("%s: import succeeded: %s", target, piece)
    requirements = [
        requirement_creg.invite(req)
        for req in piece.requirements
        ]
    for req in requirements:
        log.info("%s: requirement: %s", target, req)
    target.process_job_result(requirements)


def incomplete_result(piece, request, job_pool):
    target = job_pool.job_finished(piece.target)
    log.info("%s: import is incomplete: %s", target, piece)


def failed_result(piece, request, job_pool):
    target = job_pool.job_finished(piece.target)
    log.info("%s: import failed: %s", target, piece)


def internal_error_result(piece, request, job_pool):
    target = job_pool.job_finished(piece.target)
    log.error("%s: import job error: %s\n%s", target, piece.error, ''.join(piece.traceback))
