import cProfile

from .code.system import System


def system_main(connection, received_refs, system_config_piece, root_name, **kw):
    with cProfile.Profile() as pr:
        system = System()
        system.load_static_config(system_config_piece)
        system['init_hook'].run_hooks()
        system.run(root_name, connection, received_refs, **kw)

    profile_path = f'/tmp/rc-driver.prof'
    pr.dump_stats(profile_path)
    log.info("Written profile: %s", profile_path)

