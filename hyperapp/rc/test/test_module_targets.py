from pathlib import Path
from types import SimpleNamespace

import pytest

from hyperapp.boot.resource.workspace import Workspace

from test_probe_jobs import worker


PROGRAMS = Path(__file__).parent / 'resources' / 'test_module_imports'


@pytest.fixture
def graph(worker):
    compiler = worker.animate('rc:compile:compile.module')
    tree = {(f'{name}.dyn.py',): (PROGRAMS / f'{name}.dyn.py').read_bytes() for name in ['subject', 'checks']}
    modules = compiler._collect_modules({'sample': tree})
    targets = compiler.TargetSet({'sample': SimpleNamespace(imports={})}, modules, {})
    return SimpleNamespace(
        compiler=compiler, modules={module.path.path[-1]: module for module in modules}, targets=targets,
        requirements=worker.animate('rc:code_req:code_req.module'),
        )


def _finish_import(module, requirements=(), functions=()):
    target = module.import_tgt
    target.job_started()
    target.process_succeeded_job_result(requirements, functions)
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
    assert checks.module_tgt.state.name == 'FAILED'


def test_incomplete_first_import_waits_before_creating_retry(graph):
    graph.compiler._create_targets(graph.modules.values(), graph.targets, {})
    checks = graph.modules['checks']
    subject = graph.modules['subject']
    req = graph.requirements.TestedCodeReq(checks.path, ('tested', 'code'), ('tested', 'code', 'subject'))
    checks.import_tgt.job_started()
    checks.import_tgt.process_incomplete_job_result([req])
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
    assert subject.module_tgt is not None
    assert subject.module_tgt.state.name == 'FAILED'
    assert checks.module_tgt is None


def test_tested_provider_waits_for_its_own_project_classification(worker):
    compiler = worker.animate('rc:compile:compile.module')
    workspace = Workspace.from_yaml_file(PROGRAMS.parent / 'classification_projects' / 'workspace.yaml')
    modules = compiler._collect_modules(workspace.load_file_tree())
    targets = compiler.TargetSet(workspace.projects, modules, {})
    compiler._create_targets(modules, targets, {})
    by_name = {module.path.path[-1]: module for module in modules}
    checks, subject, other = (by_name[name] for name in ['checks', 'subject', 'other'])
    reqs = worker.animate('rc:code_req:code_req.module')
    function = worker.animate('rc:job/test.t:test_function')('test_ok', (), False, False)
    _finish_import(checks, [
        reqs.TestedCodeReq(checks.path, ('tested', 'code'), ('tested', 'code', 'lib', 'subject')),
        ], [function])
    test = targets['test/sample/checks/test_ok/0']
    _finish_import(subject)
    assert subject.module_tgt is None
    assert subject.import_alias_tgt.state.name == 'WAITING'
    assert test.state.name == 'WAITING'
    _finish_import(other)
    assert checks.module_tgt in subject.module_tgt.deps
    assert test.state.name == 'RUNNABLE'
