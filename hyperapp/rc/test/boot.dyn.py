import logging

from .code.system import setup_system
from .data.base.config import config as base_config
from .data.rc.config import config as rc_config
from .data.rc_test.config import config as rc_test_config
from .data import test_main_svc

log = logging.getLogger(__name__)


def boot(projects, project_to_tree, worker_count):
    log.info("RC test boot: %s", ', '.join(projects))
    service_creg = setup_system([base_config, rc_config, rc_test_config])
    test_main = service_creg.animate(test_main_svc)
    return test_main(projects, project_to_tree, worker_count)
