from . import htypes
from .services import (
    mosaic,
    )


def make_partial(fn_piece, **kw):
    return htypes.builtin.partial(
        function=mosaic.put(fn_piece),
        params=tuple(
            htypes.builtin.partial_param(
                name=name,
                value=mosaic.put(value),
                )
            for name, value in kw.items()
            ),
        )
