# Known bugs

Bugs noticed while working on something else and left unfixed. Remove an entry once it is fixed.
Bugs already marked with a TODO in the code are not listed here.

## rc

- **Lone auto-generated `.resources.yaml` crashes compile.** `_collect_modules` in
  `hyperapp/rc/compile.dyn.py` treats a module with an auto-generated `.resources.yaml` as compiled
  and reads its `.dyn.py` source. A module that has only the `.resources.yaml` fails there with
  `KeyError`. (Found 2026-10-04.)
