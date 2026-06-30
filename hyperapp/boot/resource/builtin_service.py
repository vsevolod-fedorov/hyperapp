import logging

from hyperapp.boot.htypes.builtin_service import builtin_service_t

log = logging.getLogger(__name__)


def make_builtin_name_to_service(pyobj_creg, mosaic, web, source_path):
    return {
        'pyobj_creg': pyobj_creg,
        'mosaic': mosaic,
        'web': web,
        'source_path': source_path,
        }


def builtin_service_name_to_piece(name):
    return builtin_service_t(name)


def builtin_service_pyobj(piece, builtin_name_to_service):
    return builtin_name_to_service[piece.name]
