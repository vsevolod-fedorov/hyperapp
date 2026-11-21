Resource compiler design
------------------------

Compiler (``compile.dyn.py``) makes ``.resources.yaml`` files for dyn modules of workspace projects.
Work is a graph of targets; jobs of runnable targets are run by subprocess workers, results update the graph.
Worker count is given to it (``--workers`` of ``main``, 2 by default); it decides which jobs share a worker.
It returns ``CompileResult``: generated files, target states, errors for direct failures and cycle
members, dependency cycles, and accepted constructor payloads by provider.
``CompileResult.succeeded`` is true only if every target resolved, including tests that contribute
no resources. The CLI writes the available resource tree before returning exit status 0 for success
or 1 for failure. A failed consumer test therefore fails the build without discarding the provider's
files (``test/test_cli.py``).
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
An ordinary module's retry keeps previously forced imports and resolves the requirement that stopped
this attempt. Merely importing another provider does not wait for that provider's tests: the two may
share a test module. Using its value at import time still needs the completed provider. All observed
requirements are validated, and the successful import supplies the final module's dependencies
(``probe_import_retries``).
For a local dynamic ``tested.code`` subject this supplies an active recorded provider, with its own imports
resolved as for a test job. The retry waits for its import alias and dependencies. Waiting for its
completed module would cycle through these tests (``probes``, ``constructor_import_cache``).
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
must activate recorded providers while importing the test module: its top-level calls need probes
immediately, and cached objects must stay instrumented for later test jobs (``probes``,
``constructor_import_cache``).
The job's activation map keeps each module's provider Path and full ref together as ``ActiveModule``;
the marker layer uses its paths and declaration replay checks its refs.
``test/test_probe_jobs.py`` checks a fresh worker importing an active provider and reusing the exact
cached probe in a test. ``probe_import_retries`` checks a second import retry and import-only service
uses through another tested provider, with one and four workers.

Activation is a non-nested job scope, cleaned by ``finally`` after success, failure and incomplete execution.
Its module map and provider paths are dropped, and the registry keeps no per-job template objects or service
resolver. Consecutive attempts and jobs, including failed and incomplete test runs, therefore start with fresh
activation state (``marker_incomplete``, ``marker_test_isolation``). There is no
constructor publication from a failed or incomplete job. Successful jobs carry a serialized constructor
snapshot, described below; marker execution itself does not change master targets.

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
incomplete execution. Discovery entries are discarded on exit; the constructor collector must already have
serialized successful entries into a candidate snapshot before that cleanup.
The sink stays generic: unrelated entries are never inspected or serialized by the constructor collector.
``test/test_probe_jobs.py`` checks these boundaries using the real worker config and job entry points,
including mutation isolation after success, failure and incomplete jobs, and release of job subsystems;
``probes`` and ``probe_isolation`` run with one and four subprocess workers.

Constructors
++++++++++++

``constructor.dyn.py:Constructor(path, key)`` is the minimal concrete constructor protocol. ``path``
is the provider's ``rc.path.Path``, and ``key`` is a nonempty, provider-local semantic identity, including
the constructor kind where necessary. It is not a generated resource name. ``piece`` returns the concrete
serializable payload; its type is registered with ``rc_constructor_creg`` to a pure ``from_piece`` actor.
The actor reconstructs a ``Constructor`` with the same path, key and payload. These are the only hooks
implemented here: resource/component generation and provider-target hooks are not part of this stage.

The wire envelope ``constructor.constructor`` contains ``path``, ``key`` and the payload ref. Successful
import and test result pieces carry ``constructors: ref list`` of these envelopes. Other result types have
no constructor field. The worker serializes pieces, not live constructors, probes, services or callbacks.

``ctr_collector`` is a job service seeded alongside ``probe_context`` before subsystem setup. It uses that
context's state and discovery sink, with no separate context or discovery lifetime. Markers receive it by
service reference; cached probes resolve ``COLLECTOR_REF`` through their current ``context.invite``.
``add_constructor(ctr, fn)`` adds a typed invocation discovery; ``declare(ctr, fn)`` records a stable
import-time declaration. Both use ``real_fn(fn).__module__`` to verify the exact active module and its
provider Path. A cached probe from an inactive module, including the test module itself, adds neither.
Generic entries stay opaque; only ``ConstructorDiscovery`` and ``ConstructorDeclaration`` entries belong
to this channel.

Publication is a success barrier, not part of scope exit. An import job finishes module animation and test
function discovery; a test job finishes the entire sync/async/generator execution. While still inside
``job_active``, it captures and serializes a candidate snapshot. Only after scope cleanup and requirement
collection both succeed does it construct a successful result. Any execution, discovery, serialization,
requirement or cleanup failure discards the candidate. Constructor collection/serialization failures,
including declaration failures wrapped by the Python importer, use the internal-error result channel.
Execution failures retain the failed/incomplete channels. Transmission is outside the scope in every case.

Cached declarations
~~~~~~~~~~~~~~~~~~~

Cached animation does not repeat decorators. ``declare`` therefore serializes immediately during module
import and stores an immutable ``ModuleDeclarations`` record on that exact Python module: the full
recorded module ref, provider Path piece and declaration refs. The module must still be initializing.
The record contains no job-bound objects, and lives only as long as that cached module. If module animation
fails, the Python importer drops the module and its metadata. A completely imported module may remain
cached even if its containing test later fails; its import-time declarations are still valid for replay.

Snapshot collection reads declaration metadata only for the job's exact active recorded modules and checks
both the full module ref and provider Path. A changed source or recorder configuration produces a different
identity, so cannot reuse old declarations. Declarations go through the same sink when first made and are
deduplicated with replayed refs. Invocation discoveries are never written to module metadata: a failed test
followed by a successful one recovers declarations without recovering failed-test observations. Test modules'
own declarations are validated but not attached on the master, and their cached probes remain excluded
when tests run. They produce no final resources.

Master acceptance
~~~~~~~~~~~~~~~~~

The decoding service ``rc_constructor_creg`` maps payload types to reconstruction actors. Accepted data
lives in ``TargetSet.constructors``, a fresh ``ConstructorRegistry`` per compilation. Before finalizing a
successful target or attaching its outputs, the handler prepares the whole constructor batch: it decodes
every envelope and payload, checks ownership, key and exact piece round trip, and checks all conflicts.
First import results keep this validated candidate pending on the master until project classification.
Their attempt is complete, but module outputs are not attached yet. The pending result retains requirements,
test function descriptors and prepared constructor data, never a worker context or decoding service.
After classification, results are applied to their proper module targets; test-module constructors are excluded.
An error applying a pending result fails its original import target and discards its candidate, even when a
different module's last first result opened the barrier (``test/test_constructor_jobs.py``).
Import results may name their own provider and, for test-module retries, its recorded local subjects.
Test results may name only those local subjects. A foreign test cannot publish constructors for the
provider, even from a successful retry or a test that also records a local subject (``constructor_projects``).
The test module's own entries are validated and excluded; its import-time observations of local subjects
are accepted. This preserves calls made only at module level even if a test reuses the cached test
module without executing that code again. Decode actors and payload properties must be side-effect free.

Identity is ``(Path, key)``. Rediscovering the same serialized envelope is idempotent; another payload for
that identity is an explicit conflicting-constructor error. Conflicts with prior jobs and conflicts within
one result follow the same rule. Each ``ConstructorEntry`` keeps the envelope ref, validated payload,
reconstructed constructor and originating target name. Equivalent rediscovery preserves the first entry,
including its origin; conflict diagnostics name both the original and rejecting targets. Entries are indexed
by provider Path and then key, so retrieving a provider's constructors does not scan other providers.

Preparation does not mutate accepted data. A malformed or contradictory later entry rejects the entire batch,
leaves prior accepted data intact and fails the responsible import or test target, rather than aborting
compilation. Decoder errors include the provider, key and originating target. Result-processing errors preserve
the exception type and notes, so an exception with no message still appears in compilation diagnostics.
Once accepted, compiled providers expose reconstructed objects through ``CompiledModuleTarget.constructors``;
``CompileResult.constructors`` exposes the validated payload snapshots by provider Path, without calling
constructor hooks again. Later changes to reconstructed objects do not alter these snapshots. This does not
create resource outputs yet.

``test/test_constructors.dyn.py`` supplies a minimal test-only constructor and marker, with an import-time
declaration and call-time observation. ``test/test_constructor_jobs.py`` uses the real job entry points and
piece round trips to check attribution, opaque entries, cache reuse, changed identities and subsystem release.
``test/test_constructor_failures.py`` checks publication boundaries; ``test/test_constructor_results.py``
checks registry validation, accepted snapshot stability and atomic rejection by the configured master handlers,
including empty decoder exceptions, round-trip mismatches and conflicting successful jobs after rediscovery.
Their complete source programs are in ``test/resources/constructor_jobs``. ``constructors``,
``constructor_conflict`` and ``constructor_import_cache`` check observable accepted pieces/diagnostics
with one and four workers, including the existing second compile with generated resources loaded.

The next resource-generation stage can consume ``CompiledModuleTarget.constructors`` after its existing
import/test dependencies resolve. It still needs component/resource generation hooks and integration with
resource locations and naming. Production payload types and their decoding registrations belong with their
concrete providers; there is no service inference, service/actor provider target, project configuration,
fixture, ``ctx_actor`` or legacy ``System``/``SystemJob`` integration here.

Targets
+++++++

Each target's name format is defined only by its own ``ensure`` method or constructor. That owner may
construct the name to find or reuse its target. Other code may index or forward the supplied name, including
for job/result routing, but must not reconstruct another target's name from a copied format. Changing the
owner's format must not require changes elsewhere in production code. Names also serve logs, UI and future
command-line target selection.

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

If one recorded subject imports another through an untested module, the untested module needs the
completed subject, which waits for its tests. It is a dependency cycle (``tested_imported_indirectly``);
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
even if the cached module is not executed again by a test (``probes``, ``constructor_import_cache``).

An incomplete run gets a retry with its new imports resolved. If a test accesses a declared subject
through ordinary ``code``, the attempt fails with a mixed-import diagnostic instead of scheduling
a retry. A successful run that merely reads the second import fails the same check
(``mixed_module_imports``).

Planned resource generation, services and actors
++++++++++++++++++++++++++++++++++++++++++++++++

The following contracts apply to the remaining migration stages. The behavioral reference for services
and actors is ``132c95d88``; they will use this compiler's targets, job subsystem and runtime resource
formats. Project ownership applies to these stages too: consumers can use a published provider, but
discoveries in their tests cannot change what it publishes.

Resource output
~~~~~~~~~~~~~~~

Keep the module's importable code separate from its output roots. Dump every constructor-produced root,
even when no other resource references it, and its referenced children. Reuse the resource naming
registry; add naming context only where a piece cannot determine a unique name. Preserve manual names
and configuration, replace the previous generation at compiler-owned locations, and report collisions.
A compiler-owned configuration may have no source file; this does not make arbitrary orphaned generated
files valid. Multiple roots, nested attributes and service ``record_mt`` pieces must round-trip with
byte-identical YAML on a second compile.

Services and configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~

* Start with synchronous, zero-argument object services. ``@mark.service`` and ``@mark.service()``
  return the original function. Emit the attribute, service type and instance, an actor with its object
  adapter, and a registration in the project's service registry. Index manual providers from their
  runtime resources and configuration, not from hand-written probe wrappers. Use provider Paths;
  distinguish missing, ambiguous and known-but-not-ready providers. A previous generated registration
  for the same provider is not a duplicate declaration.
* Service parameter binding, object versus factory inference, name lookup and retry policy belong to
  concrete services, not generic probes. Keep application configuration dependencies separate from
  Python imports: ``services.*`` continues to mean boot services. Attribute discoveries to the provider
  across retries. Allow relevant import retries before declaring a provider missing, and let services
  that need no tests complete. Equivalent call bindings, including different call syntax, agree;
  contradictory final bindings fail. Check default and keyword behavior against the reference.
* Deliver job-specific configuration through the existing isolated subsystem before resolving
  dependencies. Use job-local probe state for cached instances and partials. Service parameters in tests
  need only service injection; that does not require implementing general fixtures.
* Compose configuration by controller and actual key. Document how the reference default dictionary
  controller and explicit controllers map to record, typed-dict and data-dict configurations. Config-only
  declarations can be collected at import; bind configuration before service arguments. A missing
  ordinary data key is not a typed actor requirement. The exact default-controller mapping is still open.
* A synchronous generator object service supplies its cached instance at the first yield. Its owner
  finalizes it exactly once, in reverse construction order, on success, failure or incomplete execution.
  Run finalizers while required job services still exist and before publishing success. Diagnose zero
  or multiple yields and teardown failures without losing a primary execution error. Generator
  factories remain caller-owned. Async factories can return awaitables; async object-service and
  generator lifecycles need an explicit compatibility decision.

Actors and runtime checks
~~~~~~~~~~~~~~~~~~~~~~~~~

Dispatch ``mark.actor.<registry>`` by the full marker path. An untyped actor registers a type only
after a call discovers it. A typed declaration makes the provider known earlier, but still needs a
final binding. Resolve requirements by registry identity and type against the actual registry instance;
report a missing typed entry in that context. Emit a runtime ``system.actor`` with service references
and registrations in the registry's configuration. Multiple discovered types must coexist.

Method actors must preserve descriptor order, bound receivers and the actual subclass's attribute path
for inherited methods. Check declared types against the reference actor behavior; ``ctx_actor``, UI
markers and the legacy ``System``/``SystemJob`` are outside this migration. Verify generated services
and actors by loading and invoking them in a fresh runtime without probes, as well as by comparing
second-pass output and running stateful cases with one and several workers.
