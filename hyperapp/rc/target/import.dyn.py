import logging

from . import htypes

log = logging.getLogger(__name__)


class ImportTarget:

    @classmethod
    def ensure(cls, targets, path, source):
        idx = 0
        name = f'import/{path.project}/{"/".join(path.path)}/{idx}'
        try:
            return targets[name]
        except KeyError:
            pass
        tgt = cls(targets, name, idx, path, source)
        targets[name] = tgt
        return tgt

    def __init__(self, targets, name, idx, path, source):
        self._targets = targets
        self._name = name
        self._idx = idx
        self._path = path
        self._source = source
        self._resolved = False

    def __repr__(self):
        return f"<Target:{self._name}>"

    @property
    def name(self):
        return self._name

    @property
    def runnable(self):
        return True

    @property
    def resolved(self):
        return self._resolved

    @property
    def job(self):
        return htypes.import_job.import_job(
            target=self._name,
            path=self._path.piece,
            source=self._source,
            )

    def process_job_result(self, requirements):
        self._resolved = True


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


def failed_result(piece, request, job_pool):
    target = job_pool.job_finished(piece.target)
    log.info("%s: import failed: %s", target, piece)
