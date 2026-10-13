import logging

log = logging.getLogger(__name__)


def succeeded_result(piece, request, requirement_creg, job_pool):
    target = job_pool.job_finished(piece.target)
    log.info("%s: import succeeded: %s", target, piece)
    requirements = [
        requirement_creg.invite(req)
        for req in piece.requirements
        ]
    for req in requirements:
        log.info("%s: requirement: %s", target, req)


def failed_result(piece, request, job_pool):
    target = job_pool.job_finished(piece.target)
    log.info("%s: import failed: %s", target, piece)
