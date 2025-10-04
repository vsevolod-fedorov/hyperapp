from unittest.mock import Mock

from . import htypes
from .services import (
    mosaic,
    )
from .tested.code import config_key_ctl


def test_data_cfg_resource_name():
    gen = Mock()
    config_item = htypes.cfg_item.data_cfg_item(
        key=mosaic.put('sample-key'),
        value=mosaic.put('sample-value'),
        )
    name = config_key_ctl.data_cfg_item_name(config_item, gen)
    assert name
