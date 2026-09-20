from ..htypes.builtin_service import builtin_service_t


def builtin_service_name_to_piece(name):
    return builtin_service_t(name)


def builtin_service_pyobj(piece, builtin_name_to_service):
    return builtin_name_to_service[piece.name]
