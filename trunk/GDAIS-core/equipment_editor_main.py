from PyQt4 import QtCore, QtGui
from ui.equipmenteditor_mainwindow import EquipmentEditorMainWindow

if __name__ == "__main__":
    import sys
    app = QtGui.QApplication(sys.argv)
    ui = EquipmentEditorMainWindow()
    ui.show()
    sys.exit(app.exec_())
