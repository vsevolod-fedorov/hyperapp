from PySide import QtCore, QtGui
import common.interface as common_interface
from util import uni2str
from proxy_object import ProxyObject
import proxy_registry
import view
import view_registry
from command import Command


class ObjectSelector(ProxyObject):
    pass

    ## @classmethod
    ## def from_response( cls, server, path, iface, contents ):
    ##     target_handle = contents.target
    ##     target_object = target_handle.get_object()
    ##     targeted_path = cls.construct_path(path, target_object)
    ##     object = cls(server, targeted_path, iface, target_object, target_handle)
    ##     object.set_contents(contents)
    ##     return object

    ## @staticmethod
    ## def construct_path( path, target_object ):
    ##     if isinstance(target_object, ProxyObject):
    ##         target_path = target_object.path
    ##     else:
    ##         target_path = id(target_object)  # still need to make unique path somehow...
    ##     return dict(path, target=target_path)

    ## def __init__( self, server, path, iface, target_object, target_handle ):
    ##     ProxyObject.__init__(self, server, path, iface)
    ##     self.target_object = target_object
    ##     self.target_handle = target_handle

    ## def get_title( self ):
    ##     return '%s -> %s' % (self.path, self.target.path)

    ## def get_commands( self ):
    ##     return [ObjectCommand('choose', 'Choose', 'Choose current object', 'Ctrl+Return')]

    ## def run_command( self, command_id, initiator_view=None, **kw ):
    ##     if command_id == 'choose':
    ##         return self.run_command_choose(initiator_view)
    ##     return self.target_object.run_command(command_id, initiator_view, **kw)

    ## def run_command_choose( self, initiator_view ):
    ##     if not isinstance(self.target_object, ProxyObject): return  # not a proxy - can not choose it
    ##     self.execute_request('choose', initiator_view, target_path=self.target_object.path)

    ## def get_target_handle( self ):
    ##     return self.target_handle

    ## def clone_and_switch( self, target_handle ):
    ##     target_object = target_handle.get_object()
    ##     path = self.construct_path(self.path, target_object)
    ##     object = ObjectSelector(self.server, path, self.iface, target_object, target_handle)
    ##     object.commands = self.commands
    ##     return object


class UnwrapObjectSelector(ProxyObject):

    def __init__( self, server, path, iface ):
        ProxyObject.__init__(self, server, path, iface)
        self.base_object = None
        self.base_handle = None

    def set_contents( self, contents ):
        ProxyObject.set_contents(self, contents)
        self.base_handle = contents.base
        self.base_object = self.base_handle.get_object()


class Handle(view.Handle):

    def __init__( self, ref, target ):
        print '*** object_selector Handle', ref, target
        assert isinstance(ref, ObjectSelector), repr(ref)
        assert isinstance(target, view.Handle), repr(target)
        view.Handle.__init__(self)
        self.ref = ref
        self.target = target

    def get_object( self ):
        return self.ref

    def construct( self, parent ):
        print 'object_selector construct', parent, self.ref.get_title(), self.target.get_object().get_title()
        return View(parent, self.ref, self.target)

    def __repr__( self ):
        return 'object_selector.Handle(%s)' % uni2str(self.ref.get_title())


class UnwrapHandle(view.Handle):

    def __init__( self, object ):
        assert isinstance(object, UnwrapObjectSelector), repr(object)
        view.Handle.__init__(self)
        self.object = object

    def get_object( self ):
        return self.object

    def construct( self, parent ):
        print 'object_selector unwrapper construct', parent, self.object.get_title(), self.object.base_object.get_title()
        return self.object.base_handle.construct(parent)

    def __repr__( self ):
        return 'object_selector.UnwrapHandle(%s)' % uni2str(self.object.get_title())


class View(view.View, QtGui.QWidget):

    def __init__( self, parent, ref, target ):
        QtGui.QWidget.__init__(self)
        view.View.__init__(self, parent)
        self.ref = ref
        self.target_view = target.construct(self)
        self.groupBox = QtGui.QGroupBox('Select object for %s' % self.ref.get_title())
        gbl = QtGui.QVBoxLayout()
        gbl.addWidget(self.target_view.get_widget())
        self.groupBox.setLayout(gbl)
        l = QtGui.QVBoxLayout()
        l.addWidget(self.groupBox)
        self.setLayout(l)

    def handle( self ):
        return Handle(self.ref, self.target_view.handle())

    def get_object( self ):
        return self.ref

    def get_object_commands( self ):
        view, commands = self.target_view.get_object_commands()
        choose_cmd = Command('choose', 'Choose', 'Choose current object', 'Ctrl+Return')
        return (self, [choose_cmd] + commands)

    def run_object_command( self, command_id ):
        if command_id != 'choose':
            self.target_view.run_object_command(command_id)

    def get_current_child( self ):
        return self.target_view

    def open( self, handle ):
        print 'object_selector open', handle
        ## if not isinstance(handle, UnwrapHandle):
        ##     new_object = self.ref.clone_and_switch(handle)
        ##     handle = Handle(new_object)
        sel_handle = Handle(self.ref, handle)
        view.View.open(self, sel_handle)

    def __del__( self ):
        print '~object_selector.View'


proxy_registry.register_iface('object_selector', ObjectSelector.from_response)
proxy_registry.register_iface('object_selector_unwrap', UnwrapObjectSelector.from_response)
## view_registry.register_view('object_selector', Handle.from_resp)
## view_registry.register_view('object_selector_unwrap', UnwrapHandle.from_resp)
common_interface.Handle.register('object_selector', Handle)
