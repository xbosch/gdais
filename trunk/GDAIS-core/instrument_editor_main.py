from PyQt4 import QtCore, QtGui
from ui.instrumenteditor_mainwindow import InstrumentEditorMainWindow

if __name__ == "__main__":
    import sys
    app = QtGui.QApplication(sys.argv)
    ui = InstrumentEditorMainWindow()
    ui.show()
    sys.exit(app.exec_())
