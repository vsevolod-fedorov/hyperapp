from pathlib import Path
from types import SimpleNamespace

import pytest

from hyperapp.boot.resource.workspace import Workspace

from test_probe_jobs import worker


PROGRAMS = Path(__file__).parent / 'resources' / 'test_module_imports'


def _module_graph(worker, extra_sources):
    compiler = worker.animate('rc:compile:compile.module')
    tree = {(f'{name}.dyn.py',): (PROGRAMS / f'{name}.dyn.py').read_bytes() for name in ['subject', 'checks']}
    tree.update(extra_sources)
    modules = compiler._collect_modules({'sample': tree})
    targets = compiler.TargetSet({'sample': SimpleNamespace(imports={})}, modules, {})
    return SimpleNamespace(
        compiler=compiler, modules={module.path.path[-1]: module for module in modules}, targets=targets,
        requirements=worker.animate('rc:code_req:code_req.module'),
        )


@pytest.fixture
def graph(worker):
    return _module_graph(worker, {})


def _finish_import(module, requirements=(), functions=()):
    target = module.import_tgt
    target.job_started()
    target.process_succeeded_job_result(requirements, (), functions, (), None)
    assert target.state.name == 'RESOLVED'


@pytest.mark.parametrize('order', [('checks', 'subject'), ('subject', 'checks')])
def test_only_classified_providers_get_compiled_targets(graph, monkeypatch, order):
    target_class = graph.compiler.code.target.module.CompiledModuleTarget
    created = []
    original = target_class.__init__

    def init(self, targets, module):
        assert module.project_imports_tgt.state.name == 'RESOLVED'
        assert all(item.first_requirements is not None for item in graph.modules.values())
        created.append(module.path)
        original(self, targets, module)

    monkeypatch.setattr(target_class, '__init__', init)
    graph.compiler._create_targets(graph.modules.values(), graph.targets, {})
    assert created == []
    assert all(module.module_tgt is None for module in graph.modules.values())
    checks = graph.modules['checks']
    subject = graph.modules['subject']
    requirements = {
        'checks': [graph.requirements.TestedCodeReq(checks.path, ('tested', 'code'), ('tested', 'code', 'subject'))],
        'subject': [],
        }
    first, last = order
    _finish_import(graph.modules[first], requirements[first])
    assert created == []
    assert all(module.type.name == 'DYNAMIC' and module.module_tgt is None for module in graph.modules.values())
    assert graph.targets['imports/sample'].state.name == 'WAITING'
    _finish_import(graph.modules[last], requirements[last])
    assert created == [subject.path]
    assert checks.is_test
    assert checks.module_tgt in subject.module_tgt.deps
    assert subject.module_tgt.state.name == 'RESOLVED'
    assert 'module/compiled/sample/checks' not in {target.name for target in graph.targets}


def test_forward_dependencies_keep_identity_across_classification(graph):
    graph.compiler._create_targets(graph.modules.values(), graph.targets, {})
    checks = graph.modules['checks']
    subject = graph.modules['subject']
    code_req = graph.requirements.CodeReq(checks.path, ('code',), ('code', 'subject'))
    code = code_req.resolve(graph.targets)
    invalid = graph.requirements.CodeReq(subject.path, ('code',), ('code', 'checks')).resolve(graph.targets)
    tested_req = graph.requirements.TestedCodeReq(checks.path, ('tested', 'code'), ('tested', 'code', 'subject'))
    tested = tested_req.resolve(graph.targets)
    dependencies = {code, invalid, tested}
    assert code.target is subject.project_imports_tgt
    assert invalid.target is checks.project_imports_tgt
    assert invalid.error is None
    assert tested.target is subject.import_alias_tgt
    _finish_import(checks, [tested_req])
    assert invalid in dependencies
    assert invalid.error is None
    assert checks.import_alias_tgt.state.name == 'WAITING'
    _finish_import(subject)
    assert invalid.error == 'Test module sample:checks cannot be imported as code'
    assert code in dependencies and tested in dependencies
    assert code_req.resolve(graph.targets) == code
    assert tested_req.resolve(graph.targets) == tested
    assert code.target is subject.module_tgt
    assert tested.target is subject.import_alias_tgt
    assert code.target.state.name == 'RESOLVED'


def test_failed_first_import_keeps_forward_dependencies_failed(graph):
    graph.compiler._create_targets(graph.modules.values(), graph.targets, {})
    checks = graph.modules['checks']
    subject = graph.modules['subject']
    dep = graph.requirements.CodeReq(checks.path, ('code',), ('code', 'subject')).resolve(graph.targets)
    subject.import_tgt.job_started()
    subject.import_tgt.job_failed('failed before classification')
    assert subject.module_tgt is None
    assert dep.target.state.name == 'FAILED'
    assert checks.module_tgt is None
    _finish_import(checks, [
        graph.requirements.TestedCodeReq(checks.path, ('tested', 'code'), ('tested', 'code', 'subject')),
        ])
    assert subject.module_tgt is None
    assert checks.module_tgt is None
    assert dep.target.state.name == 'FAILED'
    assert checks.import_alias_tgt.state.name == 'FAILED'


def test_incomplete_first_import_waits_before_creating_retry(graph):
    graph.compiler._create_targets(graph.modules.values(), graph.targets, {})
    checks = graph.modules['checks']
    subject = graph.modules['subject']
    req = graph.requirements.TestedCodeReq(checks.path, ('tested', 'code'), ('tested', 'code', 'subject'))
    checks.import_tgt.job_started()
    checks.import_tgt.process_incomplete_job_result([req], (), req)
    assert checks.module_tgt is None
    assert 'import/sample/checks/1' not in {target.name for target in graph.targets}
    assert checks.import_alias_tgt.state.name == 'WAITING'
    _finish_import(subject)
    retry = graph.targets['import/sample/checks/1']
    assert retry.module is checks
    assert retry.state.name == 'RUNNABLE'
    assert subject.module_tgt.state.name == 'WAITING'
    assert checks.import_alias_tgt.state.name == 'WAITING'


def test_deferred_requirement_error_belongs_to_its_original_import(graph):
    graph.compiler._create_targets(graph.modules.values(), graph.targets, {})
    checks = graph.modules['checks']
    subject = graph.modules['subject']
    missing = graph.requirements.CodeReq(subject.path, ('code',), ('code', 'missing'))
    _finish_import(subject, [missing])
    assert subject.module_tgt is None
    _finish_import(checks, [
        graph.requirements.TestedCodeReq(checks.path, ('tested', 'code'), ('tested', 'code', 'subject')),
        ])
    assert subject.import_tgt.state.name == 'FAILED'
    assert 'Module not found for import: code.missing' in subject.import_tgt.error
    assert checks.import_tgt.error is None
    assert graph.targets['imports/sample'].state.name == 'FAILED'


def test_failed_first_import_does_not_classify_while_another_job_is_running(graph):
    graph.compiler._create_targets(graph.modules.values(), graph.targets, {})
    checks = graph.modules['checks']
    subject = graph.modules['subject']
    checks.import_tgt.job_started()
    subject.import_tgt.job_started()
    checks.import_tgt.job_failed('first import failed')
    assert graph.targets['imports/sample'].state.name == 'FAILED'
    assert all(module.module_tgt is None for module in graph.modules.values())
    _finish_import(subject)
    assert subject.module_tgt is None
    assert checks.module_tgt is None


@pytest.mark.parametrize('incomplete', [False, True])
def test_failed_last_first_import_prevents_classification_and_replay(graph, worker, incomplete):
    graph.compiler._create_targets(graph.modules.values(), graph.targets, {})
    checks = graph.modules['checks']
    subject = graph.modules['subject']
    req = graph.requirements.TestedCodeReq(checks.path, ('tested', 'code'), ('tested', 'code', 'subject'))
    if incomplete:
        checks.import_tgt.job_started()
        checks.import_tgt.process_incomplete_job_result([req], (), req)
    else:
        function = worker.animate('rc:job/test.t:test_function')('test_ok', (), False, False)
        _finish_import(checks, [req], [function])
    subject.import_tgt.job_started()
    subject.import_tgt.job_failed('first import failed')
    assert graph.targets['imports/sample'].state.name == 'FAILED'
    assert graph.targets['project/sample'].state.name == 'FAILED'
    assert all(module.type.name == 'DYNAMIC' and module.module_tgt is None for module in graph.modules.values())
    assert not any(target.name.startswith(('module/', 'test/')) or target.name.endswith('/1')
                   for target in graph.targets)


@pytest.fixture
def project_graph(worker):
    compiler = worker.animate('rc:compile:compile.module')
    workspace = Workspace.from_yaml_file(PROGRAMS.parent / 'classification_projects' / 'workspace.yaml')
    modules = compiler._collect_modules(workspace.load_file_tree())
    targets = compiler.TargetSet(workspace.projects, modules, {})
    compiler._create_targets(modules, targets, {})
    return SimpleNamespace(
        modules={module.path.path[-1]: module for module in modules}, targets=targets,
        requirements=worker.animate('rc:code_req:code_req.module'),
        )


def _finish_library_imports(project_graph, worker):
    subject = project_graph.modules['subject']
    local = project_graph.modules['subject.tests']
    _finish_import(subject)
    assert subject.module_tgt is None
    req = project_graph.requirements.TestedCodeReq(local.path, ('tested', 'code'), ('tested', 'code', 'subject'))
    function = worker.animate('rc:job/test.t:test_function')('test_value', (), False, False)
    _finish_import(local, [req], [function])
    return project_graph.targets['test/library/subject.tests/test_value/0']


def _pass_test(test):
    assert test.state.name == 'RUNNABLE'
    test.job_started()
    test.process_succeeded_job_result((), (), (), None)


def test_foreign_test_waits_for_finished_subject(project_graph, worker):
    checks = project_graph.modules['consumer.tests']
    subject = project_graph.modules['subject']
    req = project_graph.requirements.TestedCodeReq(checks.path, ('tested', 'code'), ('tested', 'code', 'lib', 'subject'))
    checks.import_tgt.job_started()
    checks.import_tgt.process_incomplete_job_result([req], (), req)
    retry = project_graph.targets['import/sample/consumer.tests/1']
    assert checks.is_test
    assert retry.state.name == 'WAITING'
    dep = req.resolve(project_graph.targets)
    assert dep.target is subject.project_imports_tgt

    local_test = _finish_library_imports(project_graph, worker)
    assert dep.target is subject.module_tgt
    assert subject.import_alias_tgt.state.name == 'RESOLVED'
    assert retry.state.name == 'WAITING'
    _pass_test(local_test)
    assert retry.state.name == 'RUNNABLE'


def test_provider_finishes_before_foreign_classification(project_graph, worker):
    _pass_test(_finish_library_imports(project_graph, worker))
    assert project_graph.modules['consumer.tests'].module_tgt is None
    assert project_graph.targets['project/library'].state.name == 'RESOLVED'


def _reachable(root):
    seen = set()

    def visit(tgt):
        if tgt not in seen:
            seen.add(tgt)
            for dep in tgt.deps:
                visit(dep)

    visit(root)
    return seen


def test_all_and_project_include_superseded_attempts(worker):
    graph = _module_graph(worker, {('helper.dyn.py',): b''})
    targets = graph.targets
    graph.compiler._create_targets(graph.modules.values(), targets, {})
    checks = graph.modules['checks']
    subject = graph.modules['subject']
    tested = graph.requirements.TestedCodeReq(checks.path, ('tested', 'code'), ('tested', 'code', 'subject'))
    code = graph.requirements.CodeReq(checks.path, ('code',), ('code', 'helper'))
    checks.import_tgt.job_started()
    checks.import_tgt.process_incomplete_job_result([tested], (), tested)
    _finish_import(subject)
    _finish_import(graph.modules['helper'])
    retry = targets['import/sample/checks/1']
    retry.job_started()
    function = worker.animate('rc:job/test.t:test_function')('test_ok', (), False, False)
    retry.process_succeeded_job_result([tested], (), [function], (), None)
    first_test = targets['test/sample/checks/test_ok/0']
    first_test.job_started()
    first_test.process_incomplete_job_result([code], ())

    project, goal = targets['project/sample'], targets['all']
    assert set(goal.deps) == {project}
    assert _reachable(project) == set(targets) - {goal}
    assert _reachable(goal) == set(targets)
    assert project.state.name == goal.state.name == 'WAITING'
    last_test = targets['test/sample/checks/test_ok/1']
    assert list(targets.enum_runnable(goal)) == [last_test]
    last_test.job_started()
    last_test.job_failed('failed on retry')
    assert project.state.name == goal.state.name == 'FAILED'
    assert project.error is None and goal.error is None


def test_all_includes_empty_projects_and_owners_of_loaded_targets(worker):
    compiler = worker.animate('rc:compile:compile.module')
    workspace = Workspace.from_yaml_file(PROGRAMS.parent / 'type_import_projects' / 'workspace.yaml')
    tree = workspace.load_file_tree()
    resources, _ = compiler.load_resources(workspace.projects, tree)
    modules = compiler._collect_modules(tree)
    manual = compiler.Module(compiler.ModuleType.MANUAL, compiler.Path('base', ('mark',)))
    modules.append(manual)
    resources['base', ('mark',), 'mark.module'] = worker.piece('base:mark:mark.module')
    projects = {**workspace.projects, 'base': SimpleNamespace(imports={}), 'empty': SimpleNamespace(imports={})}
    targets = compiler.TargetSet(projects, modules, resources)
    compiler._create_targets(modules, targets, resources)

    drawing = compiler.Path('sample', ('drawing',))
    type_req = worker.animate('rc:type_req:type_req.module').TypeReq
    point = type_req(drawing, ('htypes',), ('htypes', 'lib', 'geometry', 'point')).resolve(targets).target
    integer = type_req(drawing, ('htypes',), ('htypes', 'builtin', 'int')).resolve(targets).target
    service_req = worker.animate('rc:boot_service_req:boot_service_req.module').BootServiceReq
    mosaic = service_req(drawing, ('services',), ('services', 'mosaic')).resolve(targets).target

    goal = targets['all']
    assert {tgt.name for tgt in goal.deps} == {
        'project/sample', 'project/library', 'project/base', 'project/empty', 'project/builtin',
        }
    assert targets['project/empty'].state.name == 'RESOLVED'
    assert point in _reachable(targets['project/library'])
    assert manual.module_tgt in _reachable(targets['project/base'])
    assert {integer, mosaic} <= _reachable(targets['project/builtin'])
    assert _reachable(goal) == set(targets)
