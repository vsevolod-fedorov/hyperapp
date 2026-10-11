import logging

log = logging.getLogger(__name__)


def succeeded_result(piece, request):
    log.info("[%s] Import succeeded: %s", request, piece)


def failed_result(piece, request):
    log.info("[%s] Import failed: %s\n%s", request, piece.error, ''.join(piece.traceback))
