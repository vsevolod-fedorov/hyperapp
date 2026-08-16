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
    inner_a = htypes.foo_a.inner_record(
        an_int=123,
        )
    inner_b = htypes.foo_b.inner_record(
        a_string='some string',
        )
    outer = htypes.sample.outer_record(
        inner_a=inner_a,
        inner_b=inner_b,
        )
    print(f"Outer record: {outer!r}")
    empty = htypes.sample.empty_record()
    print(f"Empty record: {empty!r}")
    return int_t(args[0]) * 100
