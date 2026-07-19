from .code.system import setup_system
from .data.base.config import config as base_config
from .data.rc.config import config as rc_config
from .data import main_svc


def main(args):
    print('rc main:', args)
    print('base config:', base_config)
    print('rc config:', rc_config)
    service_creg = setup_system([base_config, rc_config])
    main = service_creg.animate(main_svc)
    main()
