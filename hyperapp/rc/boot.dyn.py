from .data.base.config import config as base_config
from .data.rc.config import config as rc_config


def main(args):
    print('rc main:', args)
    print('base config:', base_config)
    print('rc config:', rc_config)
