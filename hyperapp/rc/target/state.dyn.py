from enum import Enum, auto, unique


@unique
class TargetState(Enum):
    WAITING = auto()   # Not all deps are resolved yet.
    RUNNABLE = auto()  # Deps are resolved, job can be produced. Only targets having a job get here.
    RUNNING = auto()   # Job is started.
    RESOLVED = auto()  # Job is finished or there is no job, and all deps are resolved; target result can be used.
    FAILED = auto()    # Job is failed or some dep is failed; target will never be resolved.


# Targets which states are being got, innermost last. One met again depends on itself: it would recurse forever.
_state_stack = []
# Target set -> cycle met; states are got many times, so cycles are collected, to be reported once.
_cycles = {}


# Target in a dependency cycle can never be resolved, so it is failed.
# Cycle is, for example, a tested module imported by another one through an untested module:
# that one is complete, so requires complete tested module, which waits for the test.
def _dep_state(tgt):
    if tgt in _state_stack:
        cycle = _state_stack[_state_stack.index(tgt):]
        _cycles.setdefault(frozenset(cycle), [*cycle, tgt])
        return TargetState.FAILED
    _state_stack.append(tgt)
    try:
        return tgt.state
    finally:
        _state_stack.pop()


# State of a target having no job of its own.
# Failed dep wins over waiting ones: target can not be resolved anyway, and should not be reported as waiting.
def deps_state(deps):
    states = {_dep_state(tgt) for tgt in deps}
    if TargetState.FAILED in states:
        return TargetState.FAILED
    if states <= {TargetState.RESOLVED}:
        return TargetState.RESOLVED
    return TargetState.WAITING


# Returns cycles met since last call, as target lists, first one repeated last.
# Where a cycle is entered depends on set order, so each starts from its target having the least name,
# and they are sorted: logged the same way each run.
def pop_dependency_cycles():
    cycles = []
    for cycle in _cycles.values():
        path = cycle[:-1]
        idx = path.index(min(path, key=lambda tgt: tgt.name))
        path = [*path[idx:], *path[:idx]]
        cycles.append([*path, path[0]])
    _cycles.clear()
    return sorted(cycles, key=lambda cycle: [tgt.name for tgt in cycle])
