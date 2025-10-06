from .code.mark import mark
from .code.config_ctl import data_service_config_ctl


@mark.service(ctl=data_service_config_ctl())
def column_visible_reg(config):
    return config
