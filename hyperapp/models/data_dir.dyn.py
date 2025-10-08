from pathlib import Path

from . import htypes
from .code.mark import mark
from .code.record_config import RecordConfigCtl


@mark.service(ctl=RecordConfigCtl(t=htypes.data_dir.config))
def data_dir(config):
    return Path(config.data_dir).expanduser()
