from pathlib import Path

from hyperapp.boot.htypes.deduce_value_type import is_record

from . import htypes
from .services import (
    mosaic,
    web,
    source_path,
    )


def pick_source_path_assoc(value):
    if not is_record(value, htypes.builtin.python_module):
        return None
    try:
        path = source_path[value]
    except KeyError:
        return None
    return [htypes.source_path.source_path_assoc(
        python_module=mosaic.put(value),
        path=str(path),
        )]


def implant_source_path_assoc(piece):
    module = web.summon(piece.python_module)
    source_path[module] = Path(piece.path)
