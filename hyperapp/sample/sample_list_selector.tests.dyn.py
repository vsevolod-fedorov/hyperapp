from . import htypes
from .code.context import Context
from .tested.code import sample_list_selector


def test_open():
    ctx = Context(
        value=htypes.sample_list_selector.item(123),  # Unused.
        )
    model = sample_list_selector.sample_list_open(ctx)
    assert model


def test_pick():
    ctx = Context(
        model=htypes.sample_list.sample_list(),  # Unused.
        current_item=htypes.sample_list.item(
            id=123,
            title="<unused>",
            desc="<unused>",
            ),
        )
    value = sample_list_selector.sample_list_pick(ctx)
    assert value == htypes.sample_list_selector.item(123)
    
