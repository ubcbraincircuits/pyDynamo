from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.Qt import Qt

from model import FullState, Tree, UIState, History
from files import AutoSaver, loadState, saveState, importFromMatlab

import os
import sys
import time

from .actions import FullStateActions
from .common import cursorPointer
from .initialMenu import InitialMenu
from .motility3DViewWindow import Motility3DViewWindow
from .stackWindow import StackWindow
from .tilefigs import tileFigs

class DynamoWindow(QtWidgets.QMainWindow):
    def __init__(self, app, parent=None):
        QtWidgets.QMainWindow.__init__(self, parent)
        self.app = app

        self.stackWindows = []
        self.fullState = FullState()
        self.history = History(self.fullState)
        self.fullActions = FullStateActions(self.fullState, self.history)
        self.autoSaver = AutoSaver(self.fullState)
        self.initialMenu = InitialMenu(self)

        self.root = self._setupUI()
        self.centerWindow()
        self.show()
        self.initialMenu.show()

    def _setupUI(self):
        self.setWindowTitle("Dynamo")
        self.setWindowFlags(QtCore.Qt.WindowTitleHint)
        self.setFixedSize(480, 320)

        p = self.palette()
        p.setColor(self.backgroundRole(), QtCore.Qt.black)
        self.setPalette(p)

        # Dynamo logo
        label = QtWidgets.QLabel(self)
        pixmap = QtGui.QPixmap('img/tmpLogo.png')
        label.resize(pixmap.width(), pixmap.height())
        label.setPixmap(pixmap) #.scaled(label.size(), QtCore.Qt.IgnoreAspectRatio))

        # Close button
        buttonQ = QtWidgets.QPushButton("&Close Dynamo", self)
        buttonQ.setToolTip("Clonse all Dynamo windows and exit")
        buttonQ.clicked.connect(self.quit)
        cursorPointer(buttonQ)

        root = QtWidgets.QWidget(self)
        l = QtWidgets.QVBoxLayout(root)
        l.setContentsMargins(10, 10, 10, 10)
        l.addWidget(label, 0 , QtCore.Qt.AlignHCenter)
        l.addWidget(buttonQ, 0, QtCore.Qt.AlignHCenter)
        root.setFocus()
        self.setCentralWidget(root)
        return root

    def quit(self):
        self.app.quit()

    def centerWindow(self):
        # self.resize(320, 240)
        frameGm = self.frameGeometry()
        centerPoint = QtWidgets.QDesktopWidget().availableGeometry().center()
        frameGm.moveCenter(centerPoint)
        self.move(frameGm.topLeft())

    def newFromStacks(self):
        self.openFilesAndAppendStacks()
        if len(self.stackWindows) > 0:
            self.initialMenu.hide()
            self.stackWindows[0].setFocus(Qt.ActiveWindowFocusReason)
            QtWidgets.QApplication.processEvents()
            tileFigs(self.stackWindows)

    def openFromFile(self):
        filePath, _ = QtWidgets.QFileDialog.getOpenFileName(self,
            "Open dynamo save file", "", "Dynamo files (*.dyn.gz)"
        )
        if filePath != "":
            self.fullState = loadState(filePath)
            self.history = History(self.fullState)
            self.fullActions = FullStateActions(self.fullState, self.history)
            self.autoSaver = AutoSaver(self.fullState)
            self.initialMenu.hide()
            self.makeNewWindows()

    def importFromMatlab(self):
        filePath, _ = QtWidgets.QFileDialog.getOpenFileName(self,
            "Import matlab save file", "", "Matlab file (*.mat)"
        )
        if filePath != "":
            self.fullState = importFromMatlab(filePath)
            self.history = History(self.fullState)
            self.fullActions = FullStateActions(self.fullState, self.history)
            self.autoSaver = AutoSaver(self.fullState)
            self.initialMenu.hide()
            self.makeNewWindows()

    # def closeEvent(self, event):
        # event.ignore()

    def saveToFile(self):
        if self.fullState._rootPath is not None:
            saveState(self.fullState, self.fullState._rootPath)
        else:
            self.saveToNewFile()

    def saveToNewFile(self):
        filePath, _ = QtWidgets.QFileDialog.getSaveFileName(self,
            "New dynamo save file", "", "Dynamo files (*.dyn.gz)"
        )
        if filePath != "":
            if not filePath.endswith(".dyn.gz"):
                filePath = filePath + ".dyn.gz"
            self.fullState._rootPath = filePath
            saveState(self.fullState, filePath)
            QtWidgets.QMessageBox.information(self, "Saved", "Data saved to " + filePath)

    # Global key handler for actions shared between all stack windows
    def childKeyPress(self, event, childWindow):
        key = event.key()
        ctrlPressed = (event.modifiers() & Qt.ControlModifier)
        shftPressed = (event.modifiers() & Qt.ShiftModifier)

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
            self.fullActions.changeZAxis(1)
            self.redrawAllStacks()
            return True
        elif (key == ord('2')):
            self.fullActions.changeZAxis(-1)
            self.redrawAllStacks()
            return True
        elif (key == ord('L')):
            if self.fullState.inLandmarkMode():
                self.calcLandmarkRotation()
            self.fullState.toggleLandmarkMode()
            self.redrawAllStacks()
            return True
        elif (key == ord('C')):
            if shftPressed:
                self.fullState.useColor = not self.fullState.useColor
            else:
                self.fullActions.nextChannel()
            self.redrawAllStacks()
            return True
        elif (key == ord('M')):
            viewWindow = Motility3DViewWindow(self, self.fullState.trees)
            viewWindow.show()
            return True
        elif (key == ord('S') and ctrlPressed):
            self.saveToFile()
            return True
        elif (key == ord('Z') and ctrlPressed):
            self.updateUndoStack(isRedo=shftPressed, originWindow=childWindow)
            return True

        # Handle these only while doing landmarks:
        if self.fullState.inLandmarkMode():
            if (key == Qt.Key_Return):
                self.fullState.nextLandmarkPoint(shftPressed)
                self.redrawAllStacks()
                return True
            elif (key == Qt.Key_Delete):
                msg = "Delete this landmark?"
                reply = QtWidgets.QMessageBox.question(
                    self, 'Delete?', msg, QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No
                )
                if reply == QtWidgets.QMessageBox.Yes:
                    self.history.pushState()
                    self.fullActions.deleteCurrentLandmark()
                    self.redrawAllStacks()
                    return True
        return False

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
            path = self.fullState.filePaths[i]
            if not os.path.isfile(path):
                msg = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Information,
                    "Image not found...", "Could not locate volume " + path + "\nPlease specify the new location.", parent=self)
                msg.exec()
                path, _ = QtWidgets.QFileDialog.getOpenFileName(self,
                    "New volume file location", "", "TIFF image (*.tif)"
                )
                if path == "":
                    print ("Loading cancelled, quitting...")
                    QtWidgets.QApplication.quit()
                    sys.exit(0)
                self.fullState.filePaths[i] = path

            childWindow = StackWindow(
                i,
                self.fullState.filePaths[i],
                self.fullActions,
                self.fullState.trees[i],
                self.fullState.uiStates[i],
                self
            )
            self.stackWindows.append(childWindow)
            childWindow.show()
        QtWidgets.QApplication.processEvents()
        tileFigs(self.stackWindows)

        HACK_WINDOW_TO_SELECT = 1 # POIUY
        if (len(self.fullState.uiStates) > 0):
            selectedPoint = self.fullState.uiStates[HACK_WINDOW_TO_SELECT].currentPoint()
            if selectedPoint is not None:
                self.fullActions.selectPoint(HACK_WINDOW_TO_SELECT, selectedPoint)

    def removeStackWindow(self, windowIndex):
        self.fullState.removeStack(windowIndex)
        self.stackWindows.pop(windowIndex)
        for i in range(len(self.stackWindows)):
            self.stackWindows[i].windowIndex = i

    def calcLandmarkRotation(self):
        msg = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Information,
            "Calculating rotation from landmarks...", "Calculating rotation from landmarks.", parent=self)
        msg.show()
        self.fullActions.calculateBestOrientation()
        time.sleep(5)
        msg.hide()

    # TODO - listen to full state changes.
    def maybeAutoSave(self):
        if self.autoSaver is not None:
            self.autoSaver.handleStateChange()

    def updateUndoStack(self, isRedo, originWindow=None):
        if originWindow is not None:
            originWindow.statusBar().showMessage("Redoing..." if isRedo else "Undoing...")
        closeStatus = lambda: originWindow.statusBar().clearMessage() if originWindow is not None else None

        if isRedo:
            if not self.history.redo():
                closeStatus()
                return
        else:
            if not self.history.undo():
                closeStatus()
                return

        while len(self.stackWindows) > len(self.fullState.uiStates):
            lastWindow = self.stackWindows.pop()
            lastWindow.ignoreUndoCloseEvent = True
            lastWindow.close()

        for i in range(len(self.fullState.uiStates)):
            if i < len(self.stackWindows):
                self.stackWindows[i].updateState(
                    self.fullState.filePaths[i], self.fullState.uiStates[i])
            else:
                childWindow = StackWindow(
                    i,
                    self.fullState.filePaths[i],
                    self.fullActions,
                    self.fullState.trees[i],
                    self.fullState.uiStates[i],
                    self
                )
                self.stackWindows.append(childWindow)
                childWindow.show()
        closeStatus()
