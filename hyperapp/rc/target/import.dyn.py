import logging

from . import htypes
from .services import (
    mosaic,
    )
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
    def ensure(cls, targets, path, source, module_tgt, idx=0):
        name = f'import/{path.project}/{"/".join(path.path)}/{idx}'
        try:
            return targets[name]
        except KeyError:
            pass
        tgt = cls(targets, name, idx, path, source, module_tgt)
        targets[name] = tgt
        module_tgt.set_import_tgt(tgt)
        return tgt

    def __init__(self, targets, name, idx, path, source, module_tgt):
        self._targets = targets
        self._name = name
        self._idx = idx
        self._path = path
        self._source = source
        self._module_tgt = module_tgt
        self._import_req_to_path_target = {}
        # Job lifecycle only; RUNNABLE is derived from deps in the state property.
        self._state = TargetState.WAITING

    def __repr__(self):
        return f"<Target:{self._name}>"

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        if self._state == TargetState.WAITING and all(tgt.state == TargetState.RESOLVED for tgt in self.deps):
            return TargetState.RUNNABLE
        return self._state

    @property
    def deps(self):
        return {tgt for path, tgt in self._import_req_to_path_target.values()}

    def add_import_req(self, req):
        # Deps added after the job is started would not be waited for.
        assert self._state == TargetState.WAITING, (self, self._state)
        self._import_req_to_path_target[req] = req.find_import_target(self._targets)

    # Job is produced only when runnable, so all dep targets are resolved and have results.
    @property
    def job(self):
        # Several reqs may import from the same module, giving the same cfg item.
        path_to_cfg_item = {
            import_path: req.make_cfg_item(import_path, tgt)
            for req, (import_path, tgt) in self._import_req_to_path_target.items()
            }
        return htypes.import_job.import_job(
            target=self._name,
            path=self._path.piece,
            source=self._source,
            cfg_items=tuple(mosaic.put(item) for path, item in sorted(path_to_cfg_item.items())),
            )

    def job_started(self):
        self._state = TargetState.RUNNING

    def _process_job_result(self, requirements):
        self._state = TargetState.RESOLVED

    def process_succeeded_job_result(self, requirements):
        self._process_job_result(requirements)
        for req in requirements:
            self._module_tgt.add_import_req(req)

    def process_incomplete_job_result(self, requirements):
        self._process_job_result(requirements)
        next_tgt = ImportTarget.ensure(self._targets, self._path, self._source, self._module_tgt, idx=self._idx + 1)
        for req in requirements:
            next_tgt.add_import_req(req)

    @property
    def result(self):
        return None


def _resolve_requirements(requirement_creg, requirement_refs):
    requirements = [
        requirement_creg.invite(req)
        for req in requirement_refs
        ]
    for req in requirements:
        log.info("\trequirement: %s", req)
    return requirements


def succeeded_result(piece, request, requirement_creg, job_pool):
    target = job_pool.job_finished(piece.target)
    log.info("%s: import succeeded: %s", target, piece)
    requirements = _resolve_requirements(requirement_creg, piece.requirements)
    target.process_succeeded_job_result(requirements)


def incomplete_result(piece, request, requirement_creg, job_pool):
    target = job_pool.job_finished(piece.target)
    log.info("%s: import is incomplete: %s", target, piece)
    requirements = _resolve_requirements(requirement_creg, piece.requirements)
    target.process_incomplete_job_result(requirements)


def failed_result(piece, request, job_pool):
    target = job_pool.job_finished(piece.target)
    log.info("%s: import failed: %s", target, piece)


def internal_error_result(piece, request, job_pool):
    target = job_pool.job_finished(piece.target)
    log.error("%s: import job error: %s\n%s", target, piece.error, ''.join(piece.traceback))
