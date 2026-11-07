# Known bugs

Bugs noticed while working on something else and left unfixed. Remove an entry once it is fixed.
Bugs already marked with a TODO in the code are not listed here.

## rc

- **Incomplete provider import can cycle through a shared test module.** If a provider imports another
  provider tested by the same test module, then hits an unresolved marker, its retry resolves both imports.
  That retry waits for the other provider's completed module, which waits for the shared tests, which wait
  for the first provider's import alias. Even a one-way provider import can therefore cycle. Discovering
  the cross-provider import after the marker has resolved avoids this ordering issue. (Found 2026-11-07.)
