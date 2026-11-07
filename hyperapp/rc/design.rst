Resource compiler design
------------------------

Compiler (``compile.dyn.py``) makes ``.resources.yaml`` files for dyn modules of workspace projects.
Work is a graph of targets; jobs of runnable targets are run by subprocess workers, results update the graph.
Worker count is given to it (``--workers`` of ``main``, 2 by default); it decides which jobs share a worker.
It returns ``CompileResult``: generated files, target states, errors for direct failures and cycle
members, and dependency cycles. ``CompileResult.succeeded`` is true only if every target
resolved, including tests that contribute no resources. The CLI writes the available resource tree
before returning exit status 0 for success or 1 for failure. A failed consumer test therefore fails
the build without discarding the provider's files (``test/test_cli.py``).
Tests in ``test/test_rc.py`` check these for each rule below, on a workspace in ``test/resources/``;
workspaces named below are there.

Modules
+++++++

* Manual: has a ``.resources.yaml`` without the auto-generated line. Not compiled.
  One having a ``<name>.module`` resource gets a ``module/manual/<project>/<path>`` target, resolved from the start
  to that loaded resource; code imports of it resolve to it, as written (``manual_module_import``).
  A manual module can have tests in its own project or in another. They run and report failures,
  but never generate or modify its hand-written resources (``manual_module_tested``).
* Compiled: other dyn modules. Resources are generated for them.
  A generated ``.resources.yaml`` without its matching ``.dyn.py`` is invalid workspace input:
  even loading the previous generation can require the missing source. RC names both files and
  exits before starting workers or writing output (``test_generated_resources_without_source``).
* Test: a dyn module having ``tested.code`` imports. Gives no resources; its ``test_*`` functions are run.
  Name, like ``.tests`` suffix, does not matter (``test_module_by_imports``).
* Fixtures (planned): a dyn module imported by a test or another fixtures module through ``fixtures``, for example
  ``from .fixtures.my_fixtures import something``. Fixtures modules give no generated resources.
  Their role comes from incoming imports, not their name or their own source alone. A module cannot be used
  both as fixtures and as ordinary code (including tested code); that is an error.

Each project decides the roles of its own modules. Only its own tests can contribute to its compiled
resources; another project's tests consume the result (see `Tested modules`_).
Dyn modules start as neutral ``Module`` records with type ``DYNAMIC`` and import targets only.
Classification waits for all first imports in that project:
another local module's first attempt may identify an otherwise ordinary-looking module as fixtures.
The fixtures stage will propagate roles from local tests through local fixture-to-fixture imports.
An import from another project cannot turn a provider into a fixture or change its role.
Only after the project's barrier resolves can the appropriate module targets be created.
Tests and fixtures never have a ``CompiledModuleTarget``, even provisionally (``test/test_module_targets.py``).
The barrier is implemented now; fixture imports, role propagation and mixed-use diagnostics belong to the
later fixtures stage.

Imports
+++++++

Module is imported by a job through an import recorder: imports not resolved yet are recorded,
and give requirements (``code_req.dyn.py``, ``type_req.dyn.py``, ``boot_service_req.dyn.py``). Requirement prefix
(``code``, ``tested.code``, ``htypes``, ``services``) is passed by registration, in ``job/worker_config.resources.yaml``.

One importing module must use only one prefix for a given provider: either ``code`` or ``tested.code``.
RC compares resolved module paths, so renaming a Python binding, importing another attribute, or using
another alias for the same project does not avoid the check. This applies to local, foreign and manual
subjects, across import attempts and test runs. A different module may import that provider as ordinary
code even when the test declares it as a subject (``test_collection``).

Using a recorded, not resolved object at import time makes import incomplete; next import attempt is run
with the required modules resolved (``code_import_incomplete``). Attempt without new imports fails.
For a local dynamic ``tested.code`` subject this supplies an active recorded provider, with its own imports
resolved as for a test job. The retry waits for the provider's import alias and its dependencies, rather than its completed module,
which itself waits for these tests (``probes``).
Import of a module not found, or of a manual one having no module resource, fails the importing target
(``code_import_missing``, ``manual_module_no_resource``).
Importing a test module as ordinary or tested code fails with an explicit diagnostic naming it
(``test_module_imports``, with one and four workers). Dependencies check this after classification too,
so the diagnostic does not depend on which first import finishes first.
Tests and test-module import retries also check the import dependencies of recorded providers. An alias must not
bypass an invalid code import rejected by the completed module target. Only the importer owns the
diagnostic. For example, ``code_import`` imports the test module ``checks`` as code; ``code_import.tests``
tests ``code_import`` and fails by dependency, without reporting a second import error.
The collecting first attempt remains complete; it never executed those resolved providers.

Types
+++++

Type is imported as ``htypes.<type module>.<type>``, usually by ``from . import htypes``.
Type module ``<name>.types`` is found by its name nearest to the importing module, like a code one;
``htypes.builtin.<type>`` is a builtin type.
Nearest type module is used even if it lacks the type. Types are loaded resources, resolved from the start.
Type of an imported project is imported as ``htypes.<project local name>.<type module path>.<type>``, path from
its root, as code is; local type module named like the project shadows it (``type_import_projects``).

All types seen by a module are given to its import recorders up front, so using a type never makes an import attempt
or a test run incomplete. Types used are still recorded, and only these get to module resources.
Type not found is not given, and fails the importing target (``type_import_missing``).

Types used only in functions are found when the owner's tests call them (``type_import``).
A module with no local tests gets only the types it uses at import time.

Boot services
+++++++++++++

Boot service is imported as ``services.<service name>``, usually by ``from .services import (...)``.
Boot services are the builtin ones, loaded resources ``builtin:service:<name>``, resolved from the start;
they are the same for all modules. Like types, all are given to import recorders up front, so using one never
makes an import attempt or a test run incomplete; only ones used get to module resources, and ones used only
in functions are found only when local tests call them (``boot_service_import``).
Boot service not found fails the importing target (``boot_service_import_missing``).

Markers
+++++++

``code.mark`` supports arbitrary attribute chains and bare and parameterized decorators. Outside active
modules it does not look up marker names: it is a no-op and returns the original callable unchanged
(``base/test/test_mark.py``). String and type arguments are decorator parameters, not bare callables.

Worker service ``marker_registry`` (``job/marker_registry.dyn.py``) maps a marker name tuple to a system actor.
The actor names its template function or class and the services to inject. A class template is instantiated
for each marker resolution, with the provider path as its first argument. A function template is bound with
``path=``; both forms get configured services by keyword. The provider path is ``rc.path.Path``: project name
and logical module path, never the dynamic Python name. An unknown name in an active module fails its import
with both names in the diagnostic (``marker_unknown``).

Activation maps exact dynamic Python module names to these provider paths. The name includes ``ROOT_PACKAGE``
and the content hash of the complete recorded ``python_module`` piece, so same-named modules in different
paths and projects are distinct (``markers``). Only modules in this map get real markers; every other module
animated by the same job keeps no-op behavior. Marker templates are worker-side; probe registrations and their
injected test services live in test-only worker config layers, not in generated module resources.

An import job activates its own recorded module and the exact recorded tested modules found in its config
items. A test job activates those tested modules, but not the test module itself: that module's import job
already did its discoveries.
A cached test module may keep objects decorated by that import job, but its markers are not called again by
the test job. Recorded local subjects are active both while the test module is imported and while its function runs
(``markers``).

Import retries and test jobs use the same recorded providers, including direct imports of another recorded
provider. Foreign subjects and other completed modules keep their ordinary marker behavior. A fresh worker
must activate recorded providers while importing the test module: its top-level calls need probes immediately, and the cached
objects must remain instrumented when later test jobs reuse them (``probes``).
``test/test_probe_jobs.py`` checks a fresh worker importing an active provider and reusing the exact
cached probe in a test. ``probe_import_retries`` checks a second import retry and import-only service
uses through another tested provider, with one and four workers.

Activation is a non-nested job scope, cleaned by ``finally`` after success, failure and incomplete execution.
Its module map and provider paths are dropped, and the registry keeps no per-job template objects or service
resolver. Consecutive attempts and jobs, including failed and incomplete test runs, therefore start with fresh
activation state (``marker_incomplete``, ``marker_test_isolation``). There is no
constructor result channel yet: marker execution adds no target or generated resource, so discoveries of a
failed or incomplete job can not affect either. A later channel must take discoveries only from successful
jobs.

``marker_utils.dyn.py`` exposes function validation and ``check_method_decorator_order``. Generic
recursive ``real_fn`` unwrapping and the shared order check live in ``probe.dyn.py``. Unbound
``classmethod`` and ``staticmethod`` descriptors stay visible to the order check; a bound method
preserves its receiver. Both method decorators must be outside marker and probe decorators, so Python
controls receiver binding. Probes reject the wrong order at construction, including wrapped descriptors.

Probes
++++++

``ProbeBase(path, fn)`` keeps the provider as ``rc.path.Path`` and the wrapped callable; Python module
names are not provider identities. Its ``path`` and immediate ``__wrapped__`` callable are available
outside jobs too. ``real_fn(value)`` is the single recursive, binding-aware unwrapping API; probes have
no separate ``real_fn`` property, which would lose the receiver when accessed on a bound method.
The default call delegates to the wrapped callable. Descriptors preserve instance and class binding,
including nested probes and ordinary wrappers around them; outer ``staticmethod`` keeps calls unbound.

``real_fn(value)`` follows interleaved ``real_fn`` and standard ``__wrapped__`` protocols in one traversal.
It preserves a bound receiver, rejects wrapper cycles including self-links, and does not ask proxy
``__getattr__`` for wrapper attributes. Visited wrappers stay alive during traversal so temporary bound
methods cannot reuse their identities. Test discovery uses the real function's module, signature and
sync/async/generator flags; execution still calls the outer wrapper. Discovery errors fail the import job.
``probes`` checks nested wrappers and bound methods; ``probe_isolation`` also checks parameter rejection
and generator exhaustion.

Each import or test job enters ``job_active`` from ``job/context.dyn.py`` around module animation,
discovery or test execution. It creates a fresh ``ProbeContext`` and a job subsystem. The active context is
worker-local and non-nested: a worker executes one job at a time, including its async test runner.
``probe.context`` looks up this active slot on every use.
Cached probes therefore bind to the current job even if their module is not animated again, and retain no
context of their own. Access outside a job raises.

``probe.state`` is a mutable dictionary owned by that context, distinct for every probe and job. Concrete
probes put job-local cached values and callbacks here, rather than on the cached wrapper. Context state is
keyed by identity, without invoking proxy equality or hash. ``context.discoveries.add(entry)`` stores an
opaque in-memory discovery; ``entries`` returns its current tuple. The foundation does not resolve values
or interpret discoveries. The small ``test/test_probes.dyn.py`` probe uses an injected test resolver to
exercise caching and recording, with no service-signature or object/factory inference.

Worker ``marker_registry`` owns definitions and exact marker-path lookup. It has no worker service resolver.
``marker_registry.bound(context.invite)`` binds all template dependencies to the job subsystem by resource
reference, including dependencies reached through service adapters and registry actors. The current context
is seeded as ``probe:probe_context.service`` before subsystem setup resolves any dependencies, so direct and
indirect injection use the same object. Parameter names do not select services. There is no fallback to the
worker's instantiated services or mutable registry configuration.

``base/system/system.dyn.py`` supplies ``subsystem_factory.service`` from ``setup_system``. The factory
replays the immutable configuration pieces used to build its parent; each call gets fresh service, adapter
and service-config registries, configs and lazily constructed service instances. Optional instance bindings
belong only to that subsystem and are not inherited by its children. This uses the existing subsystem
implementation and configuration controllers. Marker/test registrations from worker config layers are
therefore available to jobs without sharing their mutable instances. Transport and job dispatch continue to
use the worker subsystem. Boot services such as ``pyobj_creg``, ``mosaic`` and ``web`` retain worker lifetime.

``context.invite(service_ref)`` resolves a declared service reference through the job subsystem. Cached
probes retain resource references and resolve them on use; they must not capture injected instances or bound
resolvers in wrapper attributes. The test probe exercises a mutable service and a configured registry,
including transitive injection of the context and shared dependencies within a job.

Context exit detaches all probes by clearing the active slot and service resolver, clears every state
dictionary in place, drops the state's probe references, and clears and closes the discovery sink. The bound
marker registry also drops its resolver. A retained context or marker binding cannot resolve services after
exit, and cached probes do not keep the finished subsystem alive. A closed context cannot be reused;
a closed sink rejects new entries. Cleanup happens before result transmission, on success, failure and
incomplete execution. No discovery result channel is implemented: even successful entries stay local and
are discarded on exit. Failed or incomplete jobs cannot publish them to targets or generated resources.
``test/test_probe_jobs.py`` checks these boundaries using the real worker config and job entry points,
including mutation isolation after success, failure and incomplete jobs, and release of job subsystems;
``probes`` and ``probe_isolation`` run with one and four subprocess workers.

Targets
+++++++

Target names are user-facing: logs, UI and future command-line target selection. Dependency wiring must
use semantic identities or direct target references, not resolve targets by formatting their display names.

* ``import/<project>/<path>/<idx>``: import attempt. Next one is added while the import is incomplete.
* ``import/<project>/<path>``: import alias, follows the last attempt. Resolved when module is imported completely,
  to the module as recorded by that attempt.
* ``imports/<project>``: first import attempts determining the roles of the project's modules.
* ``module/compiled/<project>/<path>``: complete module, with all its imports resolved; its result is the resource.
  Created and added to its project only after the project imports barrier classifies it as compiled.
* ``module/manual/<project>/<path>``: manual module having a module resource; its result is that resource.
  Resources it refers to are loaded ones too: generated ones are of the previous compile.
* ``type/<project>/<type module path>/<type>``: loaded type, resolved from the start; its result is the type.
* ``boot_service/<name>``: boot service, resolved from the start; its result is the loaded service resource.
* ``module/test/<project>/<path>``: test module imports. Added after classification of the first attempts;
  holds the test configuration and readiness dependencies for its test jobs.
* ``test/<project>/<path>/<function>/<idx>``: test run. Next one is added while the run is incomplete.
* ``test/<project>/<path>/<function>``: test alias, follows the last run. Resolved when the test is passed.
* ``project/<project>``: resource output for that project. A failed compiled module prevents that
  project's output. A test-only project can have no output to block and still fail the build.

States are got from deps, by target set (``target/set.dyn.py``). A dependency cycle fails all its members.
RC logs the cycle once and includes the same message, with its hint if any, in each member's
``CompileResult.errors`` entry. A target's own error comes first, followed by its cycles in
``CompileResult.cycles`` order, separated by newlines. A target that only depends on a failure gets no entry.
Target failed by itself keeps its error; wrong import requirements fail the import attempt finding them.

First imports decide
++++++++++++++++++++

The first import attempts in a single project collectively decide:

* which of its modules are tests, fixtures or compiled modules;
* which subjects each of its test modules declares, including modules in imported projects.

Project imports target waits for first attempts only, so when it is complete, roles and tested sets are known.
No individual first result can establish that its module is compiled: incoming fixture imports may still
arrive from the same project. Compiled modules also wait for local test modules testing them and
their test aliases.

Classification requires every first attempt of the project to resolve, whether its job succeeded or was
incomplete. A failed first attempt may hide incoming fixture imports or test registrations, so none of the
project's modules can be classified from the remaining results. The failed barrier leaves them neutral:
pending results create no module targets, tests or retries, and publish no constructors. This holds regardless
of result order, including when other first jobs are still running (``test/test_module_targets.py``).
All classified module targets are created before their pending results add import dependencies, test
registrations, test functions or retries. Errors applying results after this successful classification still
fail their original import targets; they are not failures to collect the first-attempt requirements.
Classification runs on result receipt, not as a side effect of reading target state.

Forward code dependencies hold the neutral module record. While unclassified, their target is its project
imports barrier; afterwards it is the classified module target. Dependency equality/hash stay tied to the
module identity rather than the changing target, including when requirements are resolved again by a retry.
A local tested-code dependency uses the recorded import alias. The alias also waits for classification:
its own first attempt completing does not make the provider ready while its project still has first jobs running.
There is no reverse dependency on importing projects. A consumer's unfinished or failed first import
cannot hold up the library's classification or resource output (``classification_failed_importer``).
``test/test_module_targets.py`` controls result order to check both sides of this boundary.

The first attempt declares subjects by module identity, including manual and foreign modules. A later
attempt discovering a new ``tested.code`` subject fails: import subjects before anything making the
import incomplete (``tested_imported_late``, ``tested_used_by_test_run``).

Tested modules
++++++++++++++

The boundary is per subject, even when one test declares subjects in several projects:

* A dynamic subject in the test's own project is recorded. Its local tests determine what goes into
  its generated resources.
* A subject from another project is tested as a consumer sees it: the completed module, after its own
  project's contributing tests. The foreign test runs and can fail the build, but can neither add
  resources to the subject nor prevent its resources from being written. In ``classification_projects``
  the library's test contributes ``mosaic``; the consumer test that expects ``web`` fails, and the
  library still emits its module with only ``mosaic``.
* A manual subject always uses its loaded module resource as written, regardless of project.

Tested module gets its own imports, found by its import job, resolved before tests run or a test-module
import retry loads it:

* untested module: complete one, compiled before tests (``test_collection/module_4.dyn.py``);
* other local module tested by the same test module, imported directly: the same recorded one the test gets.

Direct imports between recorded subjects must also be acyclic: a resource ref cannot refer back to
the piece being built. The compiled modules report the dependency cycle; their tests fail by dependency
before RC tries to construct a job with those pieces (``tested_import_cycle``).

Tested module importing another tested one through an untested one can not work: untested one is complete,
so needs complete tested module, which waits for its tests. It is a dependency cycle (``tested_imported_indirectly``);
test module target in it gives a hint naming the three modules.

Test runs
+++++++++

Test job (``job/test.dyn.py``) imports the test module and calls the function: async ones by ``asyncio.run``,
generators are run to their end. Tests with parameters fail: fixtures are not supported yet.
Recorders are cached by worker, so used imports are cleared for each test job: they are reported
as of that test only (``tested_import_used_by_test_run``, run by one worker, and by a worker per test).

Test run can not change which modules are tested, or what they import. This is checked even when the
test returns normally: reading an unresolved import does not necessarily force its value. These fail, saying why:

* test uses a subject not declared at module level: the diagnostic names the subject module, not the
  attribute accessed, and shows the ``tested.code`` import to add (``tested_used_by_test_run``);
* tested module uses an import when the test runs, but not when it is imported (``tested_import_used_by_test_run``).

Types and boot services are the exception: a tested module takes ones its passed local test runs use, and gives them
in its resources. Being resolved from the start, they do not change what it waits for (``type_import``,
``boot_service_import``).
Test-module import retries report tested requirements separately too. They enforce the same restriction on
new code imports and add preloaded requirements from successful attempts, so import-time uses are retained
even if the cached module is not executed again by a test (``probes``).

An incomplete run gets a retry with its new imports resolved. If a test accesses a declared subject
through ordinary ``code``, the attempt fails with a mixed-import diagnostic instead of scheduling
a retry. A successful run that merely reads the second import fails the same check
(``mixed_module_imports``).
