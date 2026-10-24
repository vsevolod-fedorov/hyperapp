# Known bugs

Bugs noticed while working on something else and left unfixed. Remove an entry once it is fixed.
Bugs already marked with a TODO in the code are not listed here.

## rc

- **Lone auto-generated `.resources.yaml` crashes compile.** `_collect_modules` in
  `hyperapp/rc/compile.dyn.py` treats a module with an auto-generated `.resources.yaml` as compiled
  and reads its `.dyn.py` source. A module that has only the `.resources.yaml` fails there with
  `KeyError`. (Found 2026-10-04.)

- **Importing a manual module from a compiled one breaks target resolution.** `CodeReq.get_target`
  in `hyperapp/rc/code_req.dyn.py` returns `module.module_tgt`, which is `None` for manual modules
  (only compiled modules get one in `_create_targets`). `CompiledModuleTarget.state` then calls
  `None.state`, and `result` calls `None.result`. (Found 2026-10-15.)

- **Code import of a test module fails its importer without saying why.** Code imports resolve to the
  module's `CompiledModuleTarget` in `hyperapp/rc/target/module.dyn.py`, which is failed once the module's
  first import makes it a test module. The importer then fails only by a failed dep, with no error naming
  the cause. (Found 2026-10-24.)

- **Test jobs share recorders within a worker.** Test jobs of one test module send the same recorder
  pieces, and `CachedCodeRegistry` caches animated objects by piece. So a worker reuses one recorder
  and one module object for all such jobs it runs. `requirements` and `tested_requirements` of a test
  in `hyperapp/rc/job/test.dyn.py` then include imports used by earlier tests in that worker.
  (Found 2026-10-24.)
