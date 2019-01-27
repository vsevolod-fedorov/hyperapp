import datetime
from ..util import is_list_inst


class TypeError(Exception): pass


def join_path(*args):
    return '.'.join([_f for _f in args if _f])

def all_match(x_list, y_list):
    return all(x.match(y) for x, y in zip(x_list, y_list))


class Type(object):

    def __init__(self, full_name):
        assert full_name is None or (is_list_inst(full_name, str) and full_name), repr(full_name)
        self._full_name = full_name

    @property
    def full_name(self):
        return self._full_name

    @property
    def name(self):
        if self.full_name:
            return self.full_name[-1]
        else:
            return None

    def __instancecheck__(self, value):
        raise NotImplementedError(self.__class__)

    def instance_hash(self, value):
        raise NotImplementedError(self.__class__)
        
    def expect(self, path, value, name, expr):
        if not expr:
            self.failure(path, '%s is expected, but got: %r' % (name, value))

    def assert_(self, path, expr, desc):
        if not expr:
            self.failure(path, desc)

    def failure(self, path, desc):
        raise TypeError('%s: %s' % (path, desc))


class TPrimitive(Type):

    def __init__(self, full_name=None):
        super().__init__(full_name or ['basic', self.type_name])

    def __repr__(self):
        return 'TPrimitive<%s>' % self.get_type().__name__

    def match(self, other):
        return isinstance(other, TPrimitive) and other.type_name == self.type_name

    def __instancecheck__(self, value):
        return isinstance(value, self.get_type())

    def instance_hash(self, value):
        return hash(value)

    def get_type(self):
        return self.type


class TNone(TPrimitive):
    type_name = 'none'
    type = type(None)

class TString(TPrimitive):
    type_name = 'string'
    type = str

class TBinary(TPrimitive):
    type_name = 'binary'
    type = bytes

class TInt(TPrimitive):
    type_name = 'int'
    type = int

class TBool(TPrimitive):
    type_name = 'bool'
    type = bool

class TDateTime(TPrimitive):
    type_name = 'datetime'
    type = datetime.datetime


tNone = TNone()
tString = TString()
tBinary = TBinary()
tInt = TInt()
tBool = TBool()
tDateTime = TDateTime()


class TOptional(Type):

    def __init__(self, base_t, full_name=None):
        assert isinstance(base_t, Type), repr(base_t)
        super().__init__(full_name)
        self.base_t = base_t

    def __repr__(self):
        return 'TOptional<%r>' % self.base_t

    def match(self, other):
        return isinstance(other, TOptional) and other.base_t.match(self.base_t)

    def __instancecheck__(self, value):
        return value is None or isinstance(value, self.base_t)

    def instance_hash(self, value):
        if value is None:
            return hash(value)
        else:
            return self.base_t.instance_hash(value)


class Field(object):

    @classmethod
    def from_data(cls, registry, rec):
        return cls(rec.name, registry.resolve(rec.type))

    def __init__(self, name, type):
        assert isinstance(name, str), repr(name)
        assert isinstance(type, Type), repr(type)
        self.name = name
        self.type = type

    def isinstance(self, value):
        if not self.type:
            return True  # todo: check why
        return isinstance(value, self.type)

    def __repr__(self):
        return '%r: %r' % (self.name, self.type)

    def match(self, other):
        assert isinstance(other, Field), repr(other)
        return other.name == self.name and other.type.match(self.type)


# class for instantiated records
class Record(object):

    def __init__(self, type):
        assert isinstance(type, TRecord), repr(type)
        self._type = type

    def __str__(self):
        return ', '.join('%s=%r' % (field.name, getattr(self, field.name)) for field in self._type.fields)

    def __repr__(self):
        if self._type.full_name:
            name = '.'.join(self._type.full_name)
        else:
            name = 'Record'
#        return '%s<%d: %s>' % (name, id(self._type), self)
        return '<%s: %s>' % (name, self)

    def __eq__(self, other):
        assert isinstance(other, Record), repr(other)
        return (self._type is other._type and
                [getattr(self,  field.name) for field in self._type.fields] ==
                [getattr(other, field.name) for field in self._type.fields])

    def __hash__(self):
        return self._type.instance_hash(self)

    def _asdict(self):
        return {field.name: getattr(self, field.name) for field in self._type.fields}
        

class TRecord(Type):

    def __init__(self, fields=None, base=None, full_name=None):
        assert fields is None or is_list_inst(fields, Field), repr(fields)
        assert base is None or isinstance(base, TRecord), repr(base)
        super().__init__(full_name)
        self.fields = fields or []
        if base:
            self.fields = base.fields + self.fields
        self.base = base

    def __repr__(self):
        if self.full_name:
            return '.'.join(self.full_name)
        else:
            return 'TRecord<%d: %s>' % (id(self), ', '.join(map(repr, self.fields)))

    def match(self, other):
        return (isinstance(other, TRecord)
                and all_match(other.fields, self.fields))

    def __subclasscheck__(self, cls):
        ## print('__subclasscheck__', self, cls)
        if not isinstance(cls, TRecord):
            return False
        if cls is self:
            return True
        return issubclass(cls.base, self)

    def __call__(self, *args, **kw):
        return self.instantiate(*args, **kw)

    def get_field(self, name):
        for field in self.fields:
            if field.name == name:
                return field
        assert False, repr((name, self.fields))  # Unknown field

    def __instancecheck__(self, rec):
        ## print '__instancecheck__', self, rec
        if not isinstance(rec, Record):
            return False
        return issubclass(rec._type, self)

    def instance_hash(self, value):
        return hash(tuple(field.type.instance_hash(getattr(value, field.name)) for field in self.fields))

    def adopt_args(self, args, kw, check_unexpected=True):
        path = '<Record>'
        if check_unexpected:
            self.assert_(path, len(args) <= len(self.fields),
                         'instantiate takes at most %d arguments (%d given)' % (len(self.fields), len(args)))
        fields = dict(kw)
        for field, arg in zip(self.fields, args):
            assert field.name not in fields, 'TRecord.instantiate got multiple values for field %r' % field.name
            fields[field.name] = arg
        adopted_args = {}
        unexpected = set(fields.keys())
        ## print '*** adopt_args', fields, self, [field.name for field in self.fields]
        for field in self.fields:
            if field.name in fields:
                value = fields[field.name]
                unexpected.remove(field.name)
            else:
                if isinstance(field.type, TOptional):
                    value = None
                else:
                    raise TypeError('Record %s field is missing: %r' % (self, field.name))
            assert isinstance(value, field.type), 'Field %r is expected to be %r, but is %r' % (field.name, field.type, value)
            adopted_args[field.name] = value
        if check_unexpected:
            self.assert_(path, not unexpected,
                         'Unexpected fields: %s; allowed are: %s'
                         % (', '.join(unexpected), ', '.join(field.name for field in self.fields)))
        return adopted_args

    def instantiate_impl(self, rec, *args, **kw):
        fields = self.adopt_args(args, kw or {})
        ## print '*** instantiate', self, sorted(fields.keys()), sorted(f.name for f in self.fields), fields
        for name, val in fields.items():
            setattr(rec, name, val)

    def instantiate(self, *args, **kw):
        rec = Record(self)
        self.instantiate_impl(rec, *args, **kw)
        return rec


class TList(Type):

    def __init__(self, element_t, full_name=None):
        assert isinstance(element_t, Type), repr(element_t)
        super().__init__(full_name)
        self.element_t = element_t

    def __repr__(self):
        return 'TList<%r>' % self.element_t

    def match(self, other):
        return isinstance(other, TList) and other.element_t.match(self.element_t)

    def __instancecheck__(self, value):
        return is_list_inst(value, self.element_t)

    def instance_hash(self, value):
        return hash(tuple(self.element_t.instance_hash(element) for element in value))


class TIndexedList(TList):
    pass


tRoute = TList(tString, full_name=['builtins', 'route'])

tServerRoutes = TRecord([
    Field('public_key_der', tBinary),
    Field('routes', TList(tRoute)),
    ], full_name=['builtins', 'server_routes'])

tIfaceId = TString(full_name=['builtins', 'iface_id'])

tPath = TList(tString, full_name=['builtins', 'path'])

tUrl = TRecord([
    Field('iface', tIfaceId),
    Field('public_key_der', tBinary),
    Field('path', tPath),
    ], full_name=['builtins', 'url'])

tUrlWithRoutes = TRecord(base=tUrl, fields=[
    Field('routes', TList(tRoute)),
    ], full_name=['builtins', 'url_with_routes'])
