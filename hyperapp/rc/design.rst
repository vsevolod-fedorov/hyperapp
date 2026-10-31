Resource compiler design
------------------------

Compiler (``compile.dyn.py``) makes ``.resources.yaml`` files for dyn modules of workspace projects.
Work is a graph of targets; jobs of runnable targets are run by subprocess workers, results update the graph.
Worker count is given to it (``--workers`` of ``main``, 2 by default); it decides which jobs share a worker.
It returns ``CompileResult``: generated files, target states, errors of targets failed by themselves
(not by their deps), and dependency cycles.
Tests in ``test/test_rc.py`` check these for each rule below, on a workspace in ``test/resources/``;
workspaces named below are there.

Modules
+++++++

* Manual: has a ``.resources.yaml`` without the auto-generated line. Not compiled.
  One having a ``<name>.module`` resource gets a ``module/manual/<project>/<path>`` target, resolved from the start
  to that loaded resource; code imports of it resolve to it, as written (``manual_module_import``).
* Compiled: other dyn modules. Resources are generated for them.
* Test: a dyn module having ``tested.code`` imports. Gives no resources; its ``test_*`` functions are run.
  Name, like ``.tests`` suffix, does not matter (``test_module_by_imports``).

Imports
+++++++

Module is imported by a job through an import recorder: imports not resolved yet are recorded,
and give requirements (``code_req.dyn.py``, ``type_req.dyn.py``). Requirement prefix (``code``, ``tested.code``,
``htypes``) is passed by registration, in ``worker_config.resources.yaml``.

Using a recorded, not resolved object at import time makes import incomplete; next import attempt is run
with the required modules resolved (``code_import_incomplete``). Attempt without new imports fails.
Import of a module not found, or of a manual one having no module resource, fails the importing target
(``code_import_missing``, ``manual_module_no_resource``).

Types
+++++

Type is imported as ``htypes.<type module>.<type>``, usually by ``from . import htypes``.
Type module ``<name>.types`` is found by its name nearest to the importing module, like a code one,
but in its own project only; ``htypes.builtin.<type>`` is a builtin type.
Nearest type module is used even if it lacks the type. Types are loaded resources, resolved from the start.

All types seen by a module are given to its import recorders up front, so using a type never makes an import attempt
or a test run incomplete. Types used are still recorded, and only these get to module resources.
Type not found is not given, and fails the importing target (``type_import_missing``).

Types used only in functions are found only when tests call them: test runs are required to find all type imports
of a module (``type_import``). Untested module gets only types it uses at import time.

Targets
+++++++

* ``import/<project>/<path>/<idx>``: import attempt. Next one is added while the import is incomplete.
* ``import/<project>/<path>``: import alias, follows the last attempt. Resolved when module is imported completely,
  to the module as recorded by that attempt.
* ``imports/<project>``: first import attempts of all project modules.
* ``module/compiled/<project>/<path>``: complete module, with all its imports resolved; its result is the resource.
  Made for each dyn module up front, as code imports are resolved to it before it is known what the module is;
  added to targets and its project only when its first import attempt decides it is a compiled one.
* ``module/manual/<project>/<path>``: manual module having a module resource; its result is that resource.
  Resources it refers to are loaded ones too: generated ones are of the previous compile.
* ``type/<project>/<type module path>/<type>``: loaded type, resolved from the start; its result is the type.
* ``module/test/<project>/<path>``: test module imports. Added when the first import attempt finds
  ``tested.code`` imports; following attempts of the module use it instead of the compiled one.
* ``test/<project>/<path>/<function>/<idx>``: test run. Next one is added while the run is incomplete.
* ``test/<project>/<path>/<function>``: test alias, follows the last run. Resolved when the test is passed.
* ``project/<project>``: all compiled modules of a project. Failed one fails the whole project: no resources.

States are got from deps, by target set (``target/set.dyn.py``). Dependency cycle fails all targets in it,
and is reported.
Target failed by itself keeps its error; wrong import requirements fail the import attempt finding them.

First import decides
++++++++++++++++++++

First import attempt of each module decides:

* if it is a test module or a compiled one;
* which modules a test module tests.

Project imports target waits for first attempts only, so when it is resolved, roles and tested sets are known.
Compiled module waits for it, and for test modules testing it, and their test aliases.

Later attempt finding new ``tested.code`` imports fails, and says why (``tested_imported_late``):
import tested modules before anything making the import incomplete.

Tested modules
++++++++++++++

Test gets tested modules recorded, so tests record what tested modules use.
Manual module is tested as it is, like a code import: it is not compiled, so there is nothing to record
its uses for (``manual_module_tested``).

Tested module gets its own imports, found by its import job, resolved before tests run:

* untested module: complete one, compiled before tests (``test_collection/module_4.dyn.py``);
* other module tested by the same test module, imported directly: the same recorded one the test gets.

Tested module importing another tested one through an untested one can not work: untested one is complete,
so needs complete tested module, which waits for its tests. It is a dependency cycle (``tested_imported_indirectly``);
test module target in it gives a hint naming the three modules.

Test runs
+++++++++

Test job (``job/test.dyn.py``) imports the test module and calls the function: async ones by ``asyncio.run``,
generators are run to their end. Tests with parameters fail: fixtures are not supported yet.
Recorders are cached by worker, so used imports are cleared for each test job: they are reported
as of that test only (``tested_import_used_by_test_run``, run by one worker, and by a worker per test).

Test run can not change which modules are tested, or what they import. These fail, saying why:

* test uses a tested module not imported at test module import (``tested_used_by_test_run``);
* tested module uses an import when the test runs, but not when it is imported (``tested_import_used_by_test_run``).

Types are the exception: tested module takes types its passed test runs use, and gives them in its resources.
Being resolved from the start, they do not change what it waits for (``type_import``).

Incomplete run because of other imports of the test module gets a next run with them resolved
(``test_code_used_by_run`` in ``test_collection/modules.tests.dyn.py``).
