from .code.mark import mark


# Resolved capsule is pulled by returned ref,
# and bundled together with referred capsules.
@mark.service
def web_source(ref):
    return ref
