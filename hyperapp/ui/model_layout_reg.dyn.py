from .code.mark import mark
from .code.config_ctl import data_service_config_ctl


@mark.service(ctl=data_service_config_ctl())
def model_layout_reg(config):
    return config
