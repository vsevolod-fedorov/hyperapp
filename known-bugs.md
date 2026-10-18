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

- **Import cycles recurse forever.** `CompiledModuleTarget.state` and `.result` in
  `hyperapp/rc/target/module.dyn.py` walk into the targets of imported modules with no cycle
  detection. Two compiled modules that import each other raise `RecursionError`. (Found 2026-10-15.)
