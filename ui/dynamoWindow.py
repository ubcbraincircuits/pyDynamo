from PyQt5 import QtCore, QtWidgets
from PyQt5.Qt import Qt

from model import FullState, Tree, UIState

from .initialMenu import InitialMenu
from .stackWindow import StackWindow
from .tilefigs import tileFigs

class DynamoWindow(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        QtWidgets.QMainWindow.__init__(self, parent)

        self.stackWindows = []
        self.fullState = FullState()

        self.initialMenu = InitialMenu(self)
        self.initialMenu.show()

    def newFromStacks(self):
        filePaths, _ = QtWidgets.QFileDialog.getOpenFileNames(self,
            "Open image stacks", "", "Image files (*.tif)"
        )
        self.fullState.addFiles(filePaths)
        for i in range(len(filePaths)):
            childWindow = StackWindow(
                self.fullState.filePaths[i],
                self.fullState.trees[i],
                self.fullState.uiStates[i],
                self
            )
            self.stackWindows.append(childWindow)
            childWindow.show()
            childWindow.redraw()
        if len(filePaths) > 0:
            # TODO - on shortcut
            tileFigs(self.stackWindows)
            self.initialMenu.hide()
            self.stackWindows[0].setFocus(Qt.ActiveWindowFocusReason)

    def openFromFile(self):
        QtWidgets.QMessageBox.warning(self,
            "Coming soon...",
            "To be added after file save/load working"
        )

    # Global key handler for actions shared between all stack windows
    def childKeyPress(self, event):
        key = event.key()
        print ("DYNAMO key %d" % (key))

        if (key == ord('H')):
            self.fullState.toggleLineWidth()
            for window in self.stackWindows:
                window.redraw()
            return True
        elif (key == ord('T')):
            tileFigs(self.stackWindows)
            return True
