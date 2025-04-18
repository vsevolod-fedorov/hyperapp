from . import htypes
from .tested.code import sample_commands


async def test_open_sample_static_text():
    text = await sample_commands.open_sample_static_text()
    assert text


async def test_open_sample_wiki_text():
    text = await sample_commands.open_sample_wiki_text()
    assert text


async def test_open_sample_static_list():
    list = await sample_commands.open_sample_static_list()
    assert list


async def test_show_state():
    value = await sample_commands.show_state(model_state="sample state")
    assert value


async def test_sample_list_details():
    model = htypes.sample_list.sample_list()
    value = await sample_commands.details(model, current_idx=11)


async def test_sample_tree_info():
    model = htypes.sample_tree.sample_tree()
    value = await sample_commands.sample_tree_info(model)


def test_system_info():
    value = sample_commands.system_info()
    assert type(value) is list
