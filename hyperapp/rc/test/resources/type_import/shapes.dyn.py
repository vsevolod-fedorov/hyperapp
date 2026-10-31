from . import htypes

# Calls the type at import time; types are given to imports up front, so import is complete.
origin = htypes.sample.point(x=0, y=0)


# Gets the line type only when called, so only a test run finds it is used.
def line_to(x, y):
    return htypes.sample.line(start=origin, end=htypes.sample.point(x=x, y=y))
