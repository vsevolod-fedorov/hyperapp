from . import htypes
from .code.mark import mark


@mark.selector.open
def sample_list_open(value):
    return htypes.sample_list.sample_list()


@mark.selector.pick
def sample_list_pick(model, current_item):
    return htypes.sample_list_selector.item(
        id=current_item.id,
        )
