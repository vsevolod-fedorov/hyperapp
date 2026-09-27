import logging

from .code.system import setup_system
from .data.base.config import config as base_config
from .data.rc.config import config as rc_config
from .data.rc_test.config import config as rc_test_config
from .data import test_main_svc

log = logging.getLogger(__name__)


def boot(workspace_path):
    log.info("RC test boot: %s", workspace_path)
    service_creg = setup_system([base_config, rc_config, rc_test_config])
    test_main = service_creg.animate(test_main_svc)
    test_main(workspace_path)
