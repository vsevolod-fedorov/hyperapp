import logging

log = logging.getLogger(__name__)


def run_import_job(piece, request):
    log.info("[%s] Run import job: %s", request, piece)
