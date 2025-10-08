from unittest.mock import Mock

from . import htypes
from .services import (
    mosaic,
    pyobj_creg,
    )
from .tested.code import record_config


def test_config_ctl():
    ctl_piece = htypes.record_config.config_ctl(
        t=pyobj_creg.actor_to_ref(htypes.record_config_tests.sample_config),
        )
    ctl = record_config.RecordConfigCtl.from_piece(ctl_piece)
    assert ctl.piece == ctl_piece
