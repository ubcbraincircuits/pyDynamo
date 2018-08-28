from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.Qt import Qt

from model import FullState, Tree, UIState, History
from files import AutoSaver, loadState, saveState, importFromMatlab
from util.testableFilePicker import getOpenFileName

import os
import sys
import time

from .actions import FullStateActions
from .common import cursorPointer
from .initialMenu import InitialMenu
from .settingsWindow import SettingsWindow
from .stackListWindow import StackListWindow
from .stackWindow import StackWindow
from .tilefigs import tileFigs

class DynamoWindow(QtWidgets.QMainWindow):
    def __init__(self, app, argv):
        QtWidgets.QMainWindow.__init__(self, None)
        self.app = app

        self.stackWindows = []
        self.fullState = FullState()
        self.history = History(self.fullState)
        self.fullActions = FullStateActions(self.fullState, self.history)
        self.autoSaver = AutoSaver(self.fullState)
        self.initialMenu = InitialMenu(self)
        self.settingsWindow = SettingsWindow(self)
        self.stackList = StackListWindow(self)

        self.root = self._setupUI()
        self.centerWindow()
        self.show()

        if len(argv) == 1:
            fileToOpen = argv[0]
            if fileToOpen.endswith(".dyn.gz"):
                self.openFromFile(fileToOpen)
            elif fileToOpen.endswith(".mat"):
                self.importFromMatlab(fileToOpen)
            elif fileToOpen.endswith(".tif") or fileToOpen.endswith(".tiff"):
                self.newFromStacks([fileToOpen])
            else:
                print ("Unknown file format: " + fileToOpen)
        else:
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
        buttonQ.setToolTip("Close all Dynamo windows and exit")
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
        if self.app is not None:
            self.app.quit()

    def centerWindow(self):
        # self.resize(320, 240)
        frameGm = self.frameGeometry()
        centerPoint = QtWidgets.QDesktopWidget().availableGeometry().center()
        frameGm.moveCenter(centerPoint)
        self.move(frameGm.topLeft())

    def newFromStacks(self, filePaths=None):
        self.openFilesAndAppendStacks(filePaths)
        if len(self.stackWindows) > 0:
            self.initialMenu.hide()
            self.stackList.show()
            # Focus on the first non-closed stack window:
            QtWidgets.QApplication.processEvents()
            tileFigs(self.stackWindows)
            self.focusFirstOpenStackWindow()

    def openFromFile(self, filePath=""):
        print ("File: '%s'" % filePath)
        if filePath == "":
            filePath, _ = QtWidgets.QFileDialog.getOpenFileName(self,
                "Open dynamo save file", "", "Dynamo files (*.dyn.gz)"
            )
        if filePath != "":
            self.stackList.show()
            self.fullState = loadState(filePath)
            self.history = History(self.fullState)
            self.fullActions = FullStateActions(self.fullState, self.history)
            self.autoSaver = AutoSaver(self.fullState)
            self.initialMenu.hide()
            self.makeNewWindows()

    def importFromMatlab(self, filePath=""):
        if filePath == "":
            filePath, _ = QtWidgets.QFileDialog.getOpenFileName(self,
                "Import matlab save file", "", "Matlab file (*.mat)"
            )
        if filePath != "":
            self.stackList.show()
            self.fullState = importFromMatlab(filePath)
            self.history = History(self.fullState)
            self.fullActions = FullStateActions(self.fullState, self.history)
            self.autoSaver = AutoSaver(self.fullState)
            self.initialMenu.hide()
            self.makeNewWindows()

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

        if (key == ord('1')):
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

    # For all stacks, redraw those who have a window open:
    def redrawAllStacks(self):
        for window in self.stackWindows:
            if window is not None:
                window.dendrites.drawImage()
        self.maybeAutoSave()

    # For all stacks, move the image for those who have a window open:
    def handleDendriteMoveViewRect(self, viewRect):
        for window in self.stackWindows:
            if window is not None:
                window.dendrites.imgView.handleGlobalMoveViewRect(viewRect)
        self.maybeAutoSave()

    # Make the settings dialog visible:
    def openSettings(self):
        self.settingsWindow.openFromState(self.fullState)

    # TODO - document
    def openFilesAndAppendStacks(self, filePaths=None):
        if filePaths is None:
            filePaths = getOpenFileName(self,
                "Open image stacks", "", "Image files (*.tif)", multiFile=True
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
                self.fullState.uiStates[i],
                self
            )
            self.stackWindows.append(childWindow)
            childWindow.show()
        QtWidgets.QApplication.processEvents()
        tileFigs(self.stackWindows)
        self.stackList.updateListFromStacks()
        self.stackWindows[-1].setFocus(True)

    def removeStackWindow(self, windowIndex, deleteData=False):
        if not deleteData:
            # Mark window as none, but keep all the data around:
            self.stackWindows[windowIndex] = None
        else:
            self.fullState.removeStack(windowIndex)
            if self.stackWindows[windowIndex] is not None:
                self.stackWindows[windowIndex].ignoreUndoCloseEvent = True
                self.stackWindows[windowIndex].close()
            self.stackWindows.pop(windowIndex)
            for i in range(len(self.stackWindows)):
                if self.stackWindows[i] is not None:
                    self.stackWindows[i].updateWindowIndex(i)
        self.stackList.updateListFromStacks()

    def toggleStackWindowVisibility(self, windowIndex):
        # Recreate the window if it is hidden...
        if self.stackWindows[windowIndex] is None:
            self.stackWindows[windowIndex] = StackWindow(
                windowIndex,
                self.fullState.filePaths[windowIndex],
                self.fullActions,
                self.fullState.uiStates[windowIndex],
                self
            )
            self.stackWindows[windowIndex].show()
        # Or hide it if not:
        else:
            self.stackWindows[windowIndex].ignoreUndoCloseEvent = True
            self.stackWindows[windowIndex].close()
            self.stackWindows[windowIndex] = None
        self.stackList.updateListFromStacks()


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
            lastWindow.ignoreUndoCloseEvent = False

        for i in range(len(self.fullState.uiStates)):
            if i < len(self.stackWindows):
                if self.stackWindows[i] is not None:
                    self.stackWindows[i].updateState(
                        self.fullState.filePaths[i], self.fullState.uiStates[i])
            else:
                childWindow = StackWindow(
                    i,
                    self.fullState.filePaths[i],
                    self.fullActions,
                    self.fullState.uiStates[i],
                    self
                )
                self.stackWindows.append(childWindow)
                childWindow.show()
        closeStatus()
        self.stackList.updateListFromStacks()

    # Walk through windows, find first non-closed, and focus it.
    def focusFirstOpenStackWindow(self):
        firstStackWindow = None
        for i in range(len(self.stackWindows)):
            if self.stackWindows[i] is not None:
                firstStackWindow = self.stackWindows[i]
                break
        if firstStackWindow is not None:
            firstStackWindow.setFocus(True)
            #firstStackWindow.setFocus(Qt.ActiveWindowFocusReason)
