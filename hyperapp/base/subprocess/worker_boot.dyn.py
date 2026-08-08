from .code.system import setup_system
from .data.subprocess.config import config as subprocess_config
from .data import svc


def boot(connection, associations, received_refs, process_id, master_peer):
    service_creg = setup_system([subprocess_config])
    # Implant associations before main module is loaded so that it's paths will be available.
    implanter = service_creg.animate(svc.assoc_implanter)
    implanter.init()
    implanter.implant(associations)
    main = service_creg.animate(svc.main)
    main(connection, received_refs, process_id, master_peer)
