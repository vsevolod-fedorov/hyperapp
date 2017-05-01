import datetime
from ..util import is_list_inst


class TypeError(Exception): pass


def join_path(*args):
    return '.'.join([_f for _f in args if _f])


class Type(object):

    def __call__(self, *args, **kw):
        return self.instantiate(*args, **kw)

    def __instancecheck__(self, value):
        raise NotImplementedError(self.__class__)

    def to_data(self):
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

    def __repr__(self):
        return 'TPrimitive(%s)' % repr(self.get_type())

    def __eq__(self, other):
        return isinstance(other, TPrimitive) and other.type_name == self.type_name

    def __instancecheck__(self, value):
        return isinstance(value, self.get_type())

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

    def __init__(self, base_t):
        assert isinstance(base_t, Type), repr(base_t)
        self.base_t = base_t

    def __repr__(self):
        return 'TOptional(%r)' % self.base_t

    def __eq__(self, other):
        return isinstance(other, TOptional) and other.base_t == self.base_t

    def __instancecheck__(self, value):
        return value is None or isinstance(value, self.base_t)


class Field(object):

    @classmethod
    def from_data(cls, registry, rec):
        return cls(rec.name, registry.resolve(rec.type))

    def __init__(self, name, type, default=None):
        assert isinstance(name, str), repr(name)
        assert isinstance(type, Type), repr(type)
        assert default is None or isinstance(default, type), repr(default)
        self.name = name
        self.type = type
        self.default = default

    def isinstance(self, value):
        if not self.type:
            return True  # todo: check why
        return isinstance(value, self.type)

    def __repr__(self):
        return '%r: %r' % (self.name, self.type)

    def __eq__(self, other):
        assert isinstance(other, Field), repr(other)
        return other.name == self.name and other.type == self.type


# class for instantiated records
class Record(object):

    def __init__(self, type):
        assert isinstance(type, TRecord), repr(type)
        self._type = type

    def __repr__(self):
        return 'Record(%s)' % ', '.join(
            '%s=%s' % (field.name, getattr(self, field.name)) for field in self._type.get_fields())
    

class TRecord(Type):

    def __init__(self, fields=None, base=None):
        assert fields is None or is_list_inst(fields, Field), repr(fields)
        assert base is None or isinstance(base, TRecord), repr(base)
        self.fields = fields or []
        if base:
            self.fields = base.get_fields() + self.fields
        self.base = base

    def __repr__(self):
        return 'TRecord(%d: %s)' % (id(self), ', '.join(map(repr, self.get_fields())))

    def __eq__(self, other):
        return isinstance(other, TRecord) and other.fields == self.fields

    def __subclasscheck__(self, cls):
        ## print '__subclasscheck__', self, cls
        if not isinstance(cls, TRecord):
            return False
        if cls is self:
            return True
        return issubclass(cls.base, self)

    def get_fields(self):
        return self.fields

    def get_static_fields(self):
        return self.fields

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

    def adopt_args(self, args, kw, check_unexpected=True):
        path = '<Record>'
        tfields = self.get_fields()
        if check_unexpected:
            self.assert_(path, len(args) <= len(tfields),
                         'instantiate takes at most %d argumants (%d given)' % (len(tfields), len(args)))
        fields = dict(kw)
        for field, arg in zip(tfields, args):
            assert field.name not in fields, 'TRecord.instantiate got multiple values for field %r' % field.name
            fields[field.name] = arg
        adopted_args = {}
        unexpected = set(fields.keys())
        ## print '*** adopt_args', fields, self, [field.name for field in tfields]
        for field in tfields:
            if field.name in fields:
                value = fields[field.name]
                unexpected.remove(field.name)
            else:
                if isinstance(field.type, TOptional):
                    value = None
                elif field.default is not None:
                    value = field.default
                else:
                    raise TypeError('Record field is missing: %r' % field.name)
            assert isinstance(value, field.type), 'Field %r is expected to be %r, but is %r' % (field.name, field.type, value)
            adopted_args[field.name] = value
        if check_unexpected:
            self.assert_(path, not unexpected,
                         'Unexpected fields: %s; allowed are: %s'
                         % (', '.join(unexpected), ', '.join(field.name for field in tfields)))
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

    def __init__(self, element_t):
        assert isinstance(element_t, Type), repr(element_t)
        self.element_t = element_t

    def __repr__(self):
        return 'TList(%r)' % self.element_t

    def __eq__(self, other):
        return isinstance(other, TList) and other.element_t == self.element_t

    def __instancecheck__(self, value):
        return is_list_inst(value, self.element_t)


class TIndexedList(TList):
    pass

tRoute = TList(tString)

tServerRoutes = TRecord([
    Field('public_key_der', tBinary),
    Field('routes', TList(tRoute)),
    ])

tIfaceId = tString

tPath = TList(tString)

tUrl = TRecord([
    Field('iface', tIfaceId),
    Field('public_key_der', tBinary),
    Field('path', tPath),
    ])

tUrlWithRoutes = TRecord(base=tUrl, fields=[
    Field('routes', TList(tRoute)),
    ])

tCommand = TRecord([
    Field('command_id', tString),
    Field('kind', tString),
    Field('resource_id', TList(tString)),
    Field('is_default_command', tBool, default=False),
    ])
