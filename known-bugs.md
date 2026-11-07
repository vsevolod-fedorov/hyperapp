# Known bugs

Bugs noticed while working on something else and left unfixed. Remove an entry once it is fixed.
Bugs already marked with a TODO in the code are not listed here.

## rc

- **Lone auto-generated `.resources.yaml` crashes compile.** `_collect_modules` in
  `hyperapp/rc/compile.dyn.py` treats a module with an auto-generated `.resources.yaml` as compiled
  and reads its `.dyn.py` source. A module that has only the `.resources.yaml` fails there with
  `KeyError`. (Found 2026-10-04.)

- **Tested modules importing each other directly recurse forever.** `TestModuleTarget._recorded_module`
  in `hyperapp/rc/target/test.dyn.py` builds a tested module's recorded piece with recorded pieces of the
  tested modules it imports directly. Two tested modules importing each other raise `RecursionError`
  when a test job is made. (Found 2026-10-24.)
