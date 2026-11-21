from .code import checks, subject


# The retry needs subject, but the earlier read of checks is still an invalid code import.
assert subject.value() == 42
