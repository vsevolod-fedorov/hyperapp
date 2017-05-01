import itertools
from dateutil.tz import tzutc, tzlocal


DATETIME_FORMAT = '%d.%m.%Y %H:%M:%S'


def is_list_inst(val, cls):
    if not isinstance(val, list):
        return False
    for elt in val:
        if not isinstance(elt, cls):
            return False
    return True

def is_list_list_inst(val, cls):
    if not isinstance(val, list):
        return False
    for elt in val:
        if not is_list_inst(elt, cls):
            return False
    return True

def is_tuple_inst(val, cls):
    if not isinstance(val, tuple):
        return False
    for elt in val:
        if not isinstance(elt, cls):
            return False
    return True

# from itertools recipes
def flatten(listOfLists):
    "Flatten one level of nesting"
    return list(itertools.chain.from_iterable(listOfLists))

# todo: quote/unquote '|' chars
def encode_path(path):
    return '|'.join(path)

def decode_path(path_str):
    return path_str.split('|')

# todo: quote/unquote '|' chars
def encode_route(route):
    return '|'.join(route)

def decode_route(route_str):
    return route_str.split('|')

def dt2local_str(dt):
    if dt is None: return ''
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tzutc())  # naive -> utc
    return dt.astimezone(tzlocal()).strftime(DATETIME_FORMAT)
