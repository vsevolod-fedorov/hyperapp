from . import htypes
from .tested.code import command_config_ctl


def test_key_ctl():
    ctl = command_config_ctl.TypeStrCommandKeyCtl()
    data = ctl.item_to_data(
        key=htypes.command_config_ctl_tests.sample_piece,
        template=('sample_name', htypes.command_config_ctl_tests.sample_command()),
        )
    t, (name, command) = ctl.data_to_item(data)
    assert t is htypes.command_config_ctl_tests.sample_piece
    assert name == 'sample_name'
    assert command == htypes.command_config_ctl_tests.sample_command()


def test_config_ctl():
    piece = htypes.command_config_ctl.type_str_command_config_ctl()
    ctl = command_config_ctl.TypeStrCommandConfigCtl.from_piece(piece)
    assert ctl.piece == piece
