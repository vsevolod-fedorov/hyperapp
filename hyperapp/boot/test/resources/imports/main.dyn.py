from . import htypes
from .services import (
    mosaic,
    web,
    pyobj_creg,
    )


def main(args):
    print(f"Hello from imports main; args={args!r}")
    sample_str = 'Sample string'
    sample_str_ref = mosaic.put(sample_str)
    assert web.summon(sample_str_ref) == sample_str
    int_piece = pyobj_creg.actor_to_piece(htypes.builtin.int)
    int_t = pyobj_creg.animate(int_piece)
    assert int_t is htypes.builtin.int
    inner = htypes.sample_1.inner_record(
        an_int=123,
        )
    outer = htypes.sample_2.outer_record(
        inner=inner,
        )
    print(f"Outer record: {outer!r}")
    return int_t(args[0]) * 100
