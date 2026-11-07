from pathlib import Path
from types import SimpleNamespace

from test_probe_jobs import _cfg_items


PROGRAMS = Path(__file__).parent / 'resources' / 'constructor_jobs'


def source(name):
    return (PROGRAMS / f'{name}.dyn.py').read_text()


def path(worker, name):
    return worker.probe.code.path.Path('sample', tuple(name.split('/')))


def _import_item(worker, name, module):
    return worker.svc.mosaic.put(worker.recorder.htypes.import_recorder.import_cfg_item(
        import_path=tuple(name.split('.')), resource=worker.svc.mosaic.put(module)))


def recorded_module(worker, name, source_name=None, *, imports=None):
    cfg = (*_cfg_items(worker), *(_import_item(worker, key, module) for key, module in (imports or {}).items()))
    recorder = worker.recorder.import_recorder_piece(
        path(worker, name).piece, [worker.imports.web.summon(ref) for ref in cfg])
    return worker.recorder.recorded_python_module(name, source(source_name or name), recorder)


def config_for_tests(worker, modules):
    return (*_cfg_items(worker), *(_import_item(worker, f'tested.code.{name}', module)
                                  for name, module in modules.items()))


def run_import(worker, name, source_name=None, *, cfg_items=None, at_send=None):
    job_type = worker.animate('rc:job/import.t:import_job')
    job = job_type(
        target=f'import/sample/{name}/0',
        path=path(worker, name).piece,
        source=source(source_name or name),
        cfg_items=_cfg_items(worker) if cfg_items is None else cfg_items,
        )
    return run_import_job(worker, job, at_send=at_send)


def run_import_job(worker, job, *, at_send=None):
    return _run_job(worker, worker.imports.run_import_job, job, at_send)


def run_test(
        worker, function='test_ok', *, source_name='checks', cfg_items=None,
        is_async=False, is_generator=False, at_send=None):
    job_type = worker.animate('rc:job/test.t:test_job')
    function_type = worker.animate('rc:job/test.t:test_function')
    job = job_type(
        target=f'test/sample/checks/{function}/0',
        path=path(worker, 'checks').piece,
        source=source(source_name),
        cfg_items=_cfg_items(worker) if cfg_items is None else cfg_items,
        function=function_type(function, (), is_async, is_generator),
        )
    return run_test_job(worker, job, at_send=at_send)


def run_test_job(worker, job, *, at_send=None):
    return _run_job(worker, worker.tests.run_test_job, job, at_send)


def _run_job(worker, run, job, at_send):
    results = []

    def send_message(remote, local, result):
        assert worker.probe._active_context is None
        assert worker.imports.code.context.code.mark._active is None
        assert worker.registry._resolve_service is None
        if at_send:
            at_send()
        # Cross the serialization boundary just as the subprocess transport does.
        results.append(worker.imports.web.summon(worker.svc.mosaic.put(result)))

    run(job, SimpleNamespace(remote_peer=None, local_identity=None),
        worker.import_to_req, worker.registry, worker.subsystem_factory,
        SimpleNamespace(send_message=send_message))
    assert len(results) == 1
    return results[0]


def payloads(worker, result):
    return [worker.imports.web.summon(worker.imports.web.summon(ref).payload) for ref in result.constructors]


def values(worker, result):
    return {(str(worker.probe.code.path.Path.from_piece(piece.path)), piece.key): piece.value
            for piece in payloads(worker, result)}


def make_master(worker, programs):
    compiler = worker.animate('rc:compile:compile.module')
    tree = {(f'{name}.dyn.py',): source(program).encode() for name, program in programs.items()}
    modules = compiler._collect_modules({'sample': tree})
    modules.append(compiler.Module(compiler.ModuleType.MANUAL, compiler.Path('base', ('mark',))))
    resources = {('base', ('mark',), 'mark.module'): worker.piece('base:mark:mark.module')}
    targets = compiler.TargetSet({'sample': SimpleNamespace(imports={'base': 'base'})}, modules, resources)
    compiler._create_targets(modules, targets, resources)
    pool = SimpleNamespace(job_finished=lambda name: targets[name])
    system = worker.animate('base:system/system:system.module').setup_system([
        worker.piece('base:config:config'), worker.piece('rc:config:config'), worker.piece('rc_test:config:config'),
        ], service_instances={worker.piece('rc:job_pool:job_pool.service'): pool})
    messages = system.animate(worker.piece('base:transport/registries:message_creg.service'))
    return SimpleNamespace(targets=targets, messages=messages, system=system)


def handle(master, result):
    target = master.targets[result.target]
    target.job_started()
    master.messages.animate(result, None)
    return target


def accepted(master):
    return {str(provider): {piece.key: piece.value for piece in pieces}
            for provider, pieces in master.targets.constructors.pieces.items()}
