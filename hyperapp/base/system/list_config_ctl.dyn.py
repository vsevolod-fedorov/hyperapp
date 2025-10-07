from . import htypes
from .services import (
    mosaic,
    )
from .code.config_ctl import DictConfigCtl
from .code.config_struct_ctl import ListStructCtl


class DictListConfigCtl(DictConfigCtl):

    def __init__(self, key_ctl=None, value_ctl=None, struct_ctl=None, cfg_item_creg=None, cfg_value_creg=None):
        struct_ctl = ListStructCtl()
        super().__init__(key_ctl, value_ctl, struct_ctl, cfg_item_creg, cfg_value_creg)

    @property
    def piece(self):
        return htypes.list_config_ctl.dict_list_config_ctl(
            key_ctl=mosaic.put(self._key_ctl.piece),
            value_ctl=mosaic.put(self._value_ctl.piece),
            )
