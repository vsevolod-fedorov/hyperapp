import datetime
from .. util import is_list_inst


class TypeError(Exception): pass


def join_path( *args ):
    return '.'.join(filter(None, args))


class Type(object):

    def validate( self, path, value ):
        raise NotImplementedError(self.__class__)

    def expect( self, path, value, name, expr ):
        if not expr:
            self.failure(path, '%s is expected, but got: %r' % (name, value))

    def assert_( self, path, expr, desc ):
        if not expr:
            self.failure(path, desc)

    def failure( self, path, desc ):
        raise TypeError('%s: %s' % (path, desc))


class TPrimitive(Type):

    def validate( self, path, value ):
        self.expect(path, value, self.type_name, isinstance(value, self.get_type()))

    def get_type( self ):
        return self.type
        

class TString(TPrimitive):
    type_name = 'string'
    type = basestring

class TInt(TPrimitive):
    type_name = 'int'
    type = (int, long)

class TBool(TPrimitive):
    type_name = 'bool'
    type = bool

class TDateTime(TPrimitive):
    type_name = 'datetime'
    type = datetime.datetime


class TOptional(Type):

    def __init__( self, type ):
        assert isinstance(type, Type), repr(type)
        self.type = type

    def validate( self, path, value ):
        if value is None: return
        self.type.validate(path, value)


class Field(object):

    def __init__( self, name, type ):
        assert isinstance(name, str), repr(name)
        assert isinstance(type, Type), repr(type)
        self.name = name
        self.type = type

    def validate( self, path, value ):
        if self.type:
            self.type.validate(join_path(path, self.name), value)

    def __repr__( self ):
        return 'Field(%r, %r)' % (self.name, self.type)


# class for instantiated records
class Record(object):

    def belongs( self, t ):
        try:
            t.validate('Record', self)
            return True
        except TypeError:
            return False


class TRecord(Type):

    def __init__( self, fields=None, cls=None, base=None, want_peer_arg=False ):
        assert fields is None or is_list_inst(fields, Field), repr(fields)
        assert base is None or isinstance(base, TRecord), repr(base)
        self.fields = fields or []
        self.cls = cls
        self.want_peer_arg = want_peer_arg
        if base:
            self.fields = base.fields + self.fields

    def get_fields( self ):
        return self.fields

    def get_class( self ):
        return self.cls

    def use_class( self, cls ):
        self.cls = cls

    def validate( self, path, rec ):
        ## print '*** trecord validate', path, rec, self, [field.name for field in self.fields]
        for field in self.fields:
            ## print '  * validating', path, `rec`, `field.name`, hasattr(rec, field.name)
            self.assert_(path, hasattr(rec, field.name), 'Missing field: %s' % field.name)
            field.validate(path, getattr(rec, field.name))

    def adopt_args( self, args, kw, check_unexpected=True ):
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
        if self.want_peer_arg:
            self.assert_(path, 'peer' in fields, "Record field is missing: 'peer'")
            adopted_args['peer'] = fields['peer']
            unexpected.remove('peer')
        ## print '*** adopt_args', fields, self, [field.name for field in tfields]
        for field in tfields:
            if field.name in fields:
                value = fields[field.name]
                unexpected.remove(field.name)
            else:
                if isinstance(field.type, TOptional):
                    value = None
                else:
                    raise TypeError('Record field is missing: %r' % field.name)
            field.type.validate(join_path(path, field.name), value)
            adopted_args[field.name] = value
        if check_unexpected:
            self.assert_(path, not unexpected,
                         'Unexpected fields: %s; allowed are: %s'
                         % (', '.join(unexpected), ', '.join(field.name for field in tfields)))
        return adopted_args

    def instantiate_impl( self, args=(), kw=None, check_unexpected=True ):
        fields = self.adopt_args(args, kw or {}, check_unexpected)
        ## print '*** instantiate', self, self.cls, self.want_peer_arg, sorted(fields.keys()), sorted(f.name for f in self.fields)
        cls = self.get_class()
        if cls:
            return cls(**fields)
        else:
            rec = self.make_object()
            for name, val in fields.items():
                setattr(rec, name, val)
            return rec

    def make_object( self ):
        return Record()

    # base for usual classes
    def make_class( self ):
        class Record(object):
            type = self
            def __init__( self, *args, **kw ):
                for name, val in self.type.adopt_args(args, kw).items():
                    setattr(self, name, val)
        return Record

    def instantiate( self, *args, **kw ):
        return self.instantiate_impl(args, kw)

    def instantiate_fixed( self, *args, **kw ):
        return self.instantiate_impl(args, kw)
        

class TList(Type):

    def __init__( self, element_type ):
        assert isinstance(element_type, Type), repr(element_type)
        self.element_type = element_type

    def validate( self, path, value ):
        self.expect(path, value, 'list', isinstance(value, list))
        for idx, item in enumerate(value):
            self.element_type.validate(join_path(path, '#%d' % idx), item)


class TIndexedList(TList):
    pass


class TRow(Type):

    def __init__( self, columns ):
        assert is_list_inst(columns, Type), repr(columns)
        self.columns = columns

    def validate( self, path, value ):
        self.expect(path, value, 'list', isinstance(value, list))
        if len(value) != len(self.columns):
            self.failure(path, 'Wrong row length: %d; required length: %d' % (len(value), len(self.columns)))
        for idx, (item, type) in enumerate(zip(value, self.columns)):
            type.validate(join_path(path, '#%d' % idx), item)


class TPath(Type):

    def validate( self, path, value ):
        self.expect(path, value, 'Path (dict)', isinstance(value, dict))


tCommand = TRecord([
            Field('id', TString()),
            Field('text', TString()),
            Field('desc', TString()),
            Field('shortcut', TOptional(TString())),
            ])

Command = tCommand.instantiate
