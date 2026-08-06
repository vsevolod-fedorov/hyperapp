import logging

from hyperapp.boot.init_logging import init_logging

from .code.system import setup_system
from .data.base.config import config as base_config
from .data.rc.config import config as rc_config
from .data import main_svc

log = logging.getLogger(__name__)


def boot(args):
    init_logging('rc')
    log.info("RC boot: %s", args)
    service_creg = setup_system([base_config, rc_config])
    main = service_creg.animate(main_svc)
    main(args)
