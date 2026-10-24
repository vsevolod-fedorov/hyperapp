# Known bugs

Bugs noticed while working on something else and left unfixed. Remove an entry once it is fixed.
Bugs already marked with a TODO in the code are not listed here.

## rc

- **Lone auto-generated `.resources.yaml` crashes compile.** `_collect_modules` in
  `hyperapp/rc/compile.dyn.py` treats a module with an auto-generated `.resources.yaml` as compiled
  and reads its `.dyn.py` source. A module that has only the `.resources.yaml` fails there with
  `KeyError`. (Found 2026-10-04.)

- **Code import of a test module fails its importer without saying why.** Code imports resolve to the
  module's `CompiledModuleTarget` in `hyperapp/rc/target/module.dyn.py`, which is failed once the module's
  first import makes it a test module. The importer then fails only by a failed dep, with no error naming
  the cause. (Found 2026-10-24.)

- **Tested code import of a test module is not caught.** `TestModuleTarget.import_attempt_finished` in
  `hyperapp/rc/target/test.dyn.py` registers itself with `alias_tgt.module_tgt` of each tested module.
  If that module's first import is not finished yet, this is its `CompiledModuleTarget`; if the module
  then turns out to be a test one, its alias `module_tgt` becomes a `TestModuleTarget`, and the tester
  uses that one's import deps as a tested module's. (Found 2026-10-24.)

- **Tested modules importing each other directly recurse forever.** `TestModuleTarget._recorded_module`
  in `hyperapp/rc/target/test.dyn.py` builds a tested module's recorded piece with recorded pieces of the
  tested modules it imports directly. Two tested modules importing each other raise `RecursionError`
  when a test job is made. (Found 2026-10-24.)

- **Test jobs share recorders within a worker.** Test jobs of one test module send the same recorder
  pieces, and `CachedCodeRegistry` caches animated objects by piece. So a worker reuses one recorder
  and one module object for all such jobs it runs. `requirements` and `tested_requirements` of a test
  in `hyperapp/rc/job/test.dyn.py` then include imports used by earlier tests in that worker.
  (Found 2026-10-24.)
