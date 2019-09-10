from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.Qt import Qt

from pydynamo_brain.model import FullState, Tree, UIState, History
from pydynamo_brain.files import AutoSaver, loadState, saveState, checkIfChanged, importFromMatlab, exportToSWC, saveRemapWithMerge
from pydynamo_brain.util.testableFilePicker import getOpenFileName

import os
import sys
import time

from .actions import FullStateActions
from .analysisWindow import AnalysisWindow
from .common import centerWindow, createAndShowInfo, cursorPointer
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
        self.currentStatusMessage = None

        self.root = self._setupUI()
        centerWindow(self)
        self.show()

        if len(argv) == 1:
            fileToOpen = argv[0]
            if fileToOpen.endswith(".dyn.gz"):
                self.openFromFile(fileToOpen)
            elif fileToOpen.endswith(".mat"):
                self.importFromMatlab(fileToOpen)
            elif fileToOpen.endswith(".tif") or fileToOpen.endswith(".tiff") or fileToOpen.endswith(".lsm"):
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
        # Note: need to rebind to avoid parentWindow being set by the event handler
        buttonQ.clicked.connect(lambda: self.quitAndMaybeSave(parentWindow=self))
        cursorPointer(buttonQ)

        root = QtWidgets.QWidget(self)
        l = QtWidgets.QVBoxLayout(root)
        l.setContentsMargins(10, 10, 10, 10)
        l.addWidget(label, 0 , QtCore.Qt.AlignHCenter)
        l.addWidget(buttonQ, 0, QtCore.Qt.AlignHCenter)
        root.setFocus()
        self.setCentralWidget(root)
        return root

    def hasUnsavedData(self):
        return checkIfChanged(self.fullState, self.fullState._rootPath)

    def quitAndMaybeSave(self, parentWindow=None):
        if parentWindow is None:
            parentWindow = self
        if self.hasUnsavedData():
            msg = "Unsaved data, are you sure you want to quit?"
            reply = QtWidgets.QMessageBox.question(
                parentWindow, 'Are you sure?', msg, QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No
            )
            if reply == QtWidgets.QMessageBox.No:
                return # Don't quit!
        if self.app is not None:
            self.app.quit()

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

    def saveToFile(self, parentWindow=None):
        if parentWindow is None:
            parentWindow = self
        if self.fullState._rootPath is not None:
            saveState(self.fullState, self.fullState._rootPath)
            QtWidgets.QMessageBox.information(parentWindow, "Saved", "Data saved to " + self.fullState._rootPath)
        else:
            self.saveToNewFile(parentWindow)

    def saveToNewFile(self, parentWindow=None):
        if parentWindow is None:
            parentWindow = self
        filePath, _ = QtWidgets.QFileDialog.getSaveFileName(parentWindow,
            "New dynamo save file", "", "Dynamo files (*.dyn.gz)"
        )
        if filePath != "":
            if not filePath.endswith(".dyn.gz"):
                filePath = filePath + ".dyn.gz"
            self.fullState._rootPath = filePath
            saveState(self.fullState, filePath)
            QtWidgets.QMessageBox.information(parentWindow, "Saved", "Data saved to " + filePath)

    def exportToSWC(self, parentWindow=None):
        if parentWindow is None:
            parentWindow = self
        dirPath = QtWidgets.QFileDialog.getExistingDirectory(self,
            "Folder for SWC files", ""
        )
        if dirPath is not None and dirPath is not '':
            for path, tree in zip(self.fullState.filePaths, self.fullState.trees):
                childPath = os.path.basename(path)
                childPath = childPath.replace(".tif", "").replace(".tiff", "").replace(".mat", "")
                childPath = childPath + ".swc"
                exportToSWC(dirPath, childPath, tree, self.fullState)
        QtWidgets.QMessageBox.information(parentWindow, "Save complete", "SWC files saved!")

    # Global key handler for actions shared between all stack windows
    def childKeyPress(self, event, childWindow):
        key = event.key()
        ctrlPressed = (event.modifiers() & Qt.ControlModifier)
        shftPressed = (event.modifiers() & Qt.ShiftModifier)

        if (key == ord('1')):
            self.fullActions.changeAllZAxis(1)
            self.redrawAllStacks()
            return True
        elif (key == ord('2')):
            self.fullActions.changeAllZAxis(-1)
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

    # Either start puncta drawing, or stop
    def togglePunctaMode(self):
        if not self.fullState.inPunctaMode:
            self.updateStatusMessage("Drawing puncta...")
        else:
            self.updateStatusMessage(None)
        self.fullActions.togglePunctaMode()
        self.redrawAllStacks()

    # Either start manual registration, or stop (and maybe save)
    def toggleManualRegistration(self):
        if not self.fullState.inManualRegistrationMode:
            self.updateStatusMessage("Manual ID registration active...")
        else:
            self.updateStatusMessage(None)

        self.fullActions.toggleManualRegistration()
        self.redrawAllStacks()

    # Find a point or branch by ID:
    def findByID(self, pointOrBranchID):
        self.fullActions.findPointOrBranch(pointOrBranchID)
        self.redrawAllStacks()

    # Show analysis popup
    def openAnalysisPopup(self):
        # Note: Open a new one each time, so it has the right FullState
        # self.analysisPopup.show()
        AnalysisWindow(self).show()

    # Make the settings dialog visible:
    def openSettings(self):
        self.settingsWindow.openFromState(self.fullState)

    # Clean empty branches, show popup for changes
    def cleanEmptyBranches(self, parentWindow=None):
        if parentWindow is None:
            parentWindow = self
        nRemoved = self.fullActions.cleanEmptyBranches()
        QtWidgets.QMessageBox.information(
            parentWindow, "Branches removed!", "%d empty branches removed." % nRemoved)

    # TODO - document
    def openFilesAndAppendStacks(self, filePaths=None):
        if filePaths is None:
            filePaths = getOpenFileName(self,
                "Open image stacks", "", "Image files (*.tif *.tiff *.mat *.lsm)", multiFile=True
            )
        if len(filePaths) == 0:
            return
        offset = len(self.fullState.filePaths)
        self.fullState.addFiles(filePaths)
        self.makeNewWindows(offset)

    # Keep track of where the selected point is
    def snapshotSelectionLocation(self):
        return [
            (None if sw is None else sw.getSelectionLocation()) for sw in self.stackWindows
        ]

    def updateSelectionLocation(self, snapshot):
        if len(self.stackWindows) != len(snapshot):
            return
        for sw, location in zip(self.stackWindows, snapshot):
            if sw is not None and location is not None:
                sw.updateSelectionLocation(location)

    def makeNewWindows(self, startFrom=0):
        previousPath = None

        for i in range(startFrom, len(self.fullState.filePaths)):
            path = self.fullState.filePaths[i].replace('\\', os.sep)

            if not os.path.isfile(path):
                fixedPath = None
                if previousPath is not None:
                    # try reusing the last directory, but the old file name.
                    fixedPath = os.path.join(os.path.dirname(previousPath), os.path.basename(path))

                if fixedPath is None or not os.path.isfile(fixedPath):
                    msg = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Information,
                        "Image not found...", "Could not locate volume " + path + "\nPlease specify the new location.", parent=self)
                    msg.exec()
                    fixedPath, _ = QtWidgets.QFileDialog.getOpenFileName(self,
                        "New volume file location", "", "TIFF image (*.tif)"
                    )
                    print ("\tLoading volume from %s..." % fixedPath)
                else:
                    print ("\tLoading volume from %s..." % fixedPath)

                if fixedPath is None or fixedPath == "":
                    print ("Loading cancelled, quitting...")
                    self.quitAndMaybeSave()

                self.fullState.filePaths[i] = fixedPath
                self.fullState.uiStates[i].imagePath = fixedPath
                previousPath = fixedPath

            if self.fullState.uiStates[i].isHidden:
                self.stackWindows.append(None)
            else:
                childWindow = StackWindow(
                    i,
                    self.fullState.filePaths[i],
                    self.fullActions,
                    self.fullState.uiStates[i],
                    self
                )
                childWindow.show()
                self.updateWindowMessage(childWindow)
                self.stackWindows.append(childWindow)

        QtWidgets.QApplication.processEvents()
        tileFigs(self.stackWindows)
        self.stackList.updateListFromStacks()
        # Start with focus on the last open window:
        for lastWindow in reversed(self.stackWindows):
            if lastWindow is not None:
                lastWindow.setFocus(True)
                break

    def removeStackWindow(self, windowIndex, deleteData=False):
        if not deleteData:
            # Mark window as none, but keep all the data around:
            self.stackWindows[windowIndex] = None
            self.fullState.uiStates[windowIndex].isHidden = True
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
        if self.fullState.uiStates[windowIndex].isHidden:
            self.fullState.uiStates[windowIndex].isHidden = False
            self.stackWindows[windowIndex] = StackWindow(
                windowIndex,
                self.fullState.filePaths[windowIndex],
                self.fullActions,
                self.fullState.uiStates[windowIndex],
                self
            )
            self.stackWindows[windowIndex].show()
            self.updateWindowMessage(self.stackWindows[windowIndex])
        # Or hide it if not:
        else:
            self.fullState.uiStates[windowIndex].isHidden = True
            self.stackWindows[windowIndex].ignoreUndoCloseEvent = True
            self.stackWindows[windowIndex].close()
            self.stackWindows[windowIndex] = None
        self.stackList.updateListFromStacks()

    def updateAllPrimaryBranches(self, originWindow):
        """Update all primary branches, and show a status message while happening (as it's slow)"""
        originWindow.statusBar().showMessage("Updating all primary branches...")
        self.fullActions.updateAllPrimaryBranches()
        originWindow.statusBar().clearMessage()

    # TODO - listen to full state changes.
    def maybeAutoSave(self):
        if self.autoSaver is not None:
            self.autoSaver.handleStateChange(createAndShowInfo)

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
            newHidden = self.fullState.uiStates[i].isHidden

            if i < len(self.stackWindows):
                if newHidden:
                    # new hidden, old not hidden, so hide old and remove
                    if self.stackWindows[i] is not None:
                        self.stackWindows[i].ignoreUndoCloseEvent = True
                        self.stackWindows[i].close()
                        self.stackWindows[i] = None
                    # new hidden, old hidden, so stackWindows[i] stays None
                    else:
                        pass
                else:
                    # new shown, old shown, so update in-place:
                    if self.stackWindows[i] is not None:
                        self.stackWindows[i].updateState(
                            self.fullState.filePaths[i], self.fullState.uiStates[i])
                    # new shown, old not shown, so create new:
                    else:
                        childWindow = StackWindow(
                            i,
                            self.fullState.filePaths[i],
                            self.fullActions,
                            self.fullState.uiStates[i],
                            self
                        )
                        self.updateWindowMessage(childWindow)
                        childWindow.show()
                        self.stackWindows[i] = childWindow
            else:
                if newHidden:
                    self.stackWindows.append(None)
                else:
                    childWindow = StackWindow(
                        i,
                        self.fullState.filePaths[i],
                        self.fullActions,
                        self.fullState.uiStates[i],
                        self
                    )
                    childWindow.show()
                    self.updateWindowMessage(childWindow)
                    self.stackWindows.append(childWindow)

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

    # Force user to confirm close if they have unsaved stuff
    def closeEvent(self, e):
        print ("Preventing close")
        e.ignore()

    # Update all open windows with the same status message:
    def updateStatusMessage(self, msg):
        self.currentStatusMessage = msg
        for window in self.stackWindows:
            self.updateWindowMessage(window)

    # Update a single open window with the current status message:
    def updateWindowMessage(self, window):
        if window is not None:
            if self.currentStatusMessage is None:
                window.statusBar().clearMessage()
            else:
                window.statusBar().showMessage(self.currentStatusMessage)
