import weakref
from PySide import QtCore, QtGui


class BoundViewCommand(object):

    def __init__( self, text, desc, shortcut, class_method, inst_wref ):
        print '*** BoundViewCommand', text, desc, shortcut, class_method, inst_wref
        self.text = text
        self.desc = desc
        self.shortcut = shortcut
        self.class_method = class_method
        self.inst_wref = inst_wref  # weak ref to class instance

    def get_inst( self ):
        return self.inst_wref()

    def run( self ):
        inst = self.inst_wref()
        if inst:  # inst not yet deleted?
            self.class_method(inst)

    def make_action( self, widget ):
        action = QtGui.QAction(self.text, widget)
        if isinstance(self.shortcut, list):
            action.setShortcuts(self.shortcut)
        else:
            action.setShortcut(self.shortcut)
        action.triggered.connect(self.run)
        return action


class UnboundViewCommand(object):

    def __init__( self, text, desc, shortcut, class_method ):
        print '*** UnboundViewCommand', class_method, text, desc, shortcut
        self.text = text
        self.desc = desc
        self.shortcut = shortcut
        self.class_method = class_method

    def bind( self, inst ):
        return BoundViewCommand(self.text, self.desc, self.shortcut, self.class_method, weakref.ref(inst))


class command(object):

    def __init__( self, text, desc, shortcut ):
        self.text = text
        self.desc = desc
        self.shortcut = shortcut

    def __call__( self, class_method ):
        return UnboundViewCommand(self.text, self.desc, self.shortcut, class_method)
