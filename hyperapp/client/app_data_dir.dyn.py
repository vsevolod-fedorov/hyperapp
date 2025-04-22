from pathlib import Path
from .code.mark import mark


@mark.service
def app_data_dir():
    return Path.home() / '.local/share/hyperapp/client'
