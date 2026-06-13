from . import htypes
from .services import (
    mosaic,
    web,
    pyobj_creg,
    )


def run_tests():
    sample_str = 'Sample string'
    sample_str_ref = mosaic.put(sample_str)
    assert web.summon(sample_str_ref) == sample_str
    int_piece = pyobj_creg.actor_to_piece(htypes.builtin.int)
    int_t = pyobj_creg.animate(int_piece)
    assert int_t is htypes.builtin.int
    return 'ok'
