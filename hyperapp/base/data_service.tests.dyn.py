from . import htypes
from .tested.code import data_service


def test_config_ctl():
    ctl_piece = htypes.data_service.config_ctl()
    ctl = data_service.DataServiceConfigCtl.from_piece(ctl_piece)
    assert ctl.piece == ctl_piece
    config = {
        htypes.data_service_tests.sample_key(123): htypes.data_service_tests.sample_value('sample-value'),
        }
    data = ctl.to_data(config)
    reverse_config = ctl.from_data(data)
    assert reverse_config == config


def test_type_key_config_ctl():
    ctl_piece = htypes.data_service.type_key_config_ctl()
    ctl = data_service.TypeKeyDataServiceConfigCtl.from_piece(ctl_piece)
    assert ctl.piece == ctl_piece
    config = {
        htypes.builtin.int: htypes.data_service_tests.sample_value('sample-value'),
        }
    data = ctl.to_data(config)
    reverse_config = ctl.from_data(data)
    assert reverse_config == config
