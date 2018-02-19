from PyQt5 import QtCore, QtWidgets
from PyQt5.Qt import Qt

from model import FullState, FullStateActions, Tree, UIState
from files import AutoSaver, loadState, saveState

from .initialMenu import InitialMenu
from .stackWindow import StackWindow
from .tilefigs import tileFigs

class DynamoWindow(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        QtWidgets.QMainWindow.__init__(self, parent)

        self.stackWindows = []
        self.fullState = FullState()
        self.fullActions = FullStateActions(self.fullState)
        self.autoSaver = AutoSaver(self.fullState)

        self.initialMenu = InitialMenu(self)
        self.show()
        self.initialMenu.show()

    def newFromStacks(self):
        self.initialMenu.hide()
        self.openFilesAndAppendStacks()
        self.stackWindows[0].setFocus(Qt.ActiveWindowFocusReason)
        QtWidgets.QApplication.processEvents()
        tileFigs(self.stackWindows)

    def openFromFile(self):
        filePath, _ = QtWidgets.QFileDialog.getOpenFileName(self,
            "Open dynamo save file", "", "Dynamo files (*.dyn)"
        )
        if filePath != "":
            self.fullState = loadState(filePath)
            self.fullActions = FullStateActions(self.fullState)
            self.autoSaver = AutoSaver(self.fullState)
            self.makeNewWindows()

    def closeEvent(self, event):
        print ("CLOSE ignored")
        print (event)
        # event.ignore()

    def saveToFile(self):
        if self.fullState._rootPath is not None:
            saveState(self.fullState, self.fullState._rootPath)
        else:
            self.saveToNewFile()

    def saveToNewFile(self):
        filePath, _ = QtWidgets.QFileDialog.getSaveFileName(self,
            "New dynamo save file", "", "Dynamo files (*.dyn)"
        )
        if filePath != "":
            if not filePath.endswith(".dyn"):
                filePath = filePath + ".dyn"
            self.fullState._rootPath = filePath
            saveState(self.fullState, filePath)
            QtWidgets.QMessageBox.information(self, "Saved", "Data saved to " + filePath)

    # Global key handler for actions shared between all stack windows
    def childKeyPress(self, event):
        key = event.key()
        ctrlPressed = (event.modifiers() & Qt.ControlModifier)

        print ("DYNAMO key %d" % (key))

        if (key == ord('H')):
            self.fullState.toggleLineWidth()
            self.redrawAllStacks()
            return True
        elif (key == ord('T')):
            self.stackWindows[0].setFocus(Qt.ActiveWindowFocusReason)
            tileFigs(self.stackWindows)
            return True
        elif (key == ord('O')):
            self.openFilesAndAppendStacks()
            return True
        elif (key == ord('1')):
            self.changeZAxis(1)
            return True
        elif (key == ord('2')):
            self.changeZAxis(-1)
            return True
        elif (key == ord('C')):
            self.fullActions.nextChannel()
            self.redrawAllStacks()
            return True
        elif (key == ord('S') and ctrlPressed):
            self.saveToFile()
            return True

    # TODO: listen to state changes and redraw everything automatically?
    def changeZAxis(self, delta):
        self.fullState.changeZAxis(delta)
        self.redrawAllStacks()

    # TODO - document
    def redrawAllStacks(self):
        for window in self.stackWindows:
            window.dendrites.drawImage()
        self.maybeAutoSave()

    # TODO - document
    def handleDendriteMoveViewRect(self, viewRect):
        for window in self.stackWindows:
            # HACK - very dots, much wow.
            window.dendrites.imgView.handleGlobalMoveViewRect(viewRect)
        self.maybeAutoSave()

    # TODO - document
    def openFilesAndAppendStacks(self):
        filePaths, _ = QtWidgets.QFileDialog.getOpenFileNames(self,
            "Open image stacks", "", "Image files (*.tif)"
        )
        if len(filePaths) == 0:
            return
        offset = len(self.fullState.filePaths)
        self.fullState.addFiles(filePaths)
        self.makeNewWindows(offset)

    def makeNewWindows(self, startFrom=0):
        for i in range(startFrom, len(self.fullState.filePaths)):
            childWindow = StackWindow(
                i,
                self.fullState.filePaths[i],
                self.fullActions,
                self.fullState.uiStates[i],
                self
            )
            self.stackWindows.append(childWindow)
            childWindow.show()
        QtWidgets.QApplication.processEvents()
        tileFigs(self.stackWindows)

    def removeStackWindow(self, windowIndex):
        self.fullState.removeStack(windowIndex)
        self.stackWindows.pop(windowIndex)
        for i in range(len(self.stackWindows)):
            self.stackWindows[i].windowIndex = i

    # TODO - listen to full state changes.
    def maybeAutoSave(self):
        if self.autoSaver is not None:
            self.autoSaver.handleStateChange()
