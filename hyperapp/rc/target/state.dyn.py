from enum import Enum, auto, unique


@unique
class TargetState(Enum):
    WAITING = auto()   # Not all deps are resolved yet.
    RUNNABLE = auto()  # Deps are resolved, job can be produced. Only targets having a job get here.
    RUNNING = auto()   # Job is started.
    RESOLVED = auto()  # Job is finished or there is no job, and all deps are resolved; target result can be used.
    FAILED = auto()    # Job is failed or some dep is failed; target will never be resolved.


# State of a target having no job of its own, from states of its deps.
# Failed dep wins over waiting ones: target can not be resolved anyway, and should not be reported as waiting.
def combined_state(dep_states):
    states = set(dep_states)
    if TargetState.FAILED in states:
        return TargetState.FAILED
    if states <= {TargetState.RESOLVED}:
        return TargetState.RESOLVED
    return TargetState.WAITING
