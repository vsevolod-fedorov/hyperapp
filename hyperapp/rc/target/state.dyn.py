from enum import Enum, auto, unique


@unique
class TargetState(Enum):
    WAITING = auto()   # Not all deps are resolved yet.
    RUNNABLE = auto()  # Deps are resolved, job can be produced. Only targets having a job get here.
    RUNNING = auto()   # Job is started.
    RESOLVED = auto()  # Job is finished or there is no job, and all deps are resolved; target result can be used.
