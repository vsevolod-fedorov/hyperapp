from .code.system import setup_system
from .data.subprocess.config import config as subprocess_config
from .data import main_svc


def boot(connection, associations, received_refs, process_id, master_peer):
    service_creg = setup_system([subprocess_config])
    main = service_creg.animate(main_svc)
    main(connection, associations, received_refs, process_id, master_peer)
