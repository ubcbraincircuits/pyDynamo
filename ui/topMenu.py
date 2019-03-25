from PyQt5 import QtCore, QtWidgets

import webbrowser

from util.testableFilePicker import getOpenFileName

from .motility3DViewWindow import Motility3DViewWindow
from .tilefigs import tileFigs

class TopMenu():
    def __init__(self, stackWindow):
        self.stackWindow = stackWindow
        menuBar = stackWindow.menuBar()

        self.drawModeOnly = []
        dmo = lambda x: self.drawModeOnly.append(x)
        self.registerModeOnly = []
        rmo = lambda x: self.registerModeOnly.append(x)

        fileMenu = QtWidgets.QMenu('&File', stackWindow)
        fileMenu.addAction('&New stack...', self.appendStack, QtCore.Qt.Key_N)
        fileMenu.addAction('&Save', self.save, QtCore.Qt.CTRL + QtCore.Qt.Key_S)
        fileMenu.addAction('Save As...', self.saveAs, QtCore.Qt.CTRL + QtCore.Qt.SHIFT + QtCore.Qt.Key_S)
        fileMenu.addSeparator()
        dmo(fileMenu.addAction('Import from previous stack', self.importFromPreviousStack, QtCore.Qt.Key_I))
        dmo(fileMenu.addAction('Import from SWC...', self.importFromSWC, QtCore.Qt.CTRL + QtCore.Qt.Key_I))
        dmo(fileMenu.addAction('Export to SWC...', self.exportToSWC, QtCore.Qt.CTRL + QtCore.Qt.Key_E))
        fileMenu.addSeparator()
        fileMenu.addAction('&Project Settings...',
            self.openSettings, QtCore.Qt.CTRL + QtCore.Qt.SHIFT + QtCore.Qt.Key_P)
        fileMenu.addAction('Close &Window', self.closeWindow, QtCore.Qt.CTRL + QtCore.Qt.Key_W)
        fileMenu.addAction('Close Dynamo', self.closeDynamo, QtCore.Qt.CTRL + QtCore.Qt.SHIFT + QtCore.Qt.Key_W)
        menuBar.addMenu(fileMenu)

        editMenu = QtWidgets.QMenu('&Edit', stackWindow)
        editMenu.addAction('Undo', self.undo, QtCore.Qt.CTRL + QtCore.Qt.Key_Z)
        editMenu.addAction('Redo', self.redo, QtCore.Qt.CTRL + QtCore.Qt.SHIFT + QtCore.Qt.Key_Z)
        editMenu.addSeparator()
        editMenu.addAction('Find', self.find, QtCore.Qt.CTRL + QtCore.Qt.Key_F)
        editMenu.addSeparator()

        annotationSubmenu = editMenu.addMenu("Annotate")
        dmo(annotationSubmenu.addAction('Selected point on current stack',
            self.annotateThis, QtCore.Qt.Key_Q))
        dmo(annotationSubmenu.addAction('Selected point on all later stacks',
            self.annotateAll, QtCore.Qt.SHIFT + QtCore.Qt.Key_Q))

        dmo(editMenu.addAction('Register from previous stack', self.register, QtCore.Qt.Key_R))
        dmo(editMenu.addAction('&Replace parent', self.reparent, QtCore.Qt.CTRL + QtCore.Qt.Key_R))
        dmo(editMenu.addAction('Set as primary &branch', self.primaryBranch, QtCore.Qt.CTRL + QtCore.Qt.Key_B))
        dmo(editMenu.addAction('Clean up all primary &branches',
            self.allPrimaryBranches, QtCore.Qt.CTRL + QtCore.Qt.SHIFT + QtCore.Qt.Key_B))
        editMenu.addAction('Draw &Puncta', self.punctaMode, QtCore.Qt.Key_P)
        dmo(editMenu.addAction('Cycle select->move->reparent modes', self.cyclePointModes, QtCore.Qt.Key_Tab))

        manualRegisterSubmenu = editMenu.addMenu("Manual registration")
        manualRegisterSubmenu.addAction('Start/end',
            self.manualRegister, QtCore.Qt.CTRL + QtCore.Qt.SHIFT + QtCore.Qt.Key_R)
        rmo(manualRegisterSubmenu.addAction('Align IDs all selected points',
            self.alignIDsToFirst, QtCore.Qt.SHIFT + QtCore.Qt.Key_Return))
        rmo(manualRegisterSubmenu.addAction('Assign a new ID to all selected points',
            self.alignIDsToNew, QtCore.Qt.SHIFT + QtCore.Qt.Key_Apostrophe))
        menuBar.addMenu(editMenu)

        viewMenu = QtWidgets.QMenu('&View', stackWindow)
        viewMenu.addAction('Zoom In', self.zoomIn, QtCore.Qt.Key_X)
        viewMenu.addAction('Zoom Out', self.zoomOut, QtCore.Qt.Key_Z)
        viewMenu.addAction('View 3D Arbor', self.view3DArbor, QtCore.Qt.Key_3)
        viewMenu.addAction('View 3D Image Volume', self.view3DVolume, QtCore.Qt.SHIFT + QtCore.Qt.Key_3)

        viewMenu.addSeparator()
        dmo(viewMenu.addAction('Toggle line size', self.toggleLineSize, QtCore.Qt.Key_J))
        dmo(viewMenu.addAction('Toggle dot size', self.toggleDotSize, QtCore.Qt.SHIFT + QtCore.Qt.Key_J))
        viewMenu.addAction('Change channel', self.changeChannel, QtCore.Qt.Key_C)
        viewMenu.addAction('Turn on/off colours', self.toggleColor, QtCore.Qt.SHIFT + QtCore.Qt.Key_C)
        viewMenu.addAction('Cycle showing branches on this Z -> nearby Z -> all Z',
            self.cycleBranchDisplayMode, QtCore.Qt.Key_V)
        viewMenu.addAction('Cycle showing annotations -> IDs -> nothing per point', self.cyclePointInfo, QtCore.Qt.Key_F)
        dmo(viewMenu.addAction('Show/Hide hilighted points', self.toggleHilight, QtCore.Qt.Key_H))
        viewMenu.addAction('Show/Hide entire tree', self.toggleShowAll, QtCore.Qt.SHIFT + QtCore.Qt.Key_H)
        viewMenu.addAction('Project all Z onto one image', self.zProject, QtCore.Qt.Key_Underscore)
        viewMenu.addAction('Tile windows on screen', self.tileFigs, QtCore.Qt.Key_T)
        menuBar.addMenu(viewMenu)

        analysisMenu = QtWidgets.QMenu('&Analysis', stackWindow)
        analysisMenu.addAction('Launch analysis window', self.launchAnalysis, QtCore.Qt.CTRL + QtCore.Qt.SHIFT + QtCore.Qt.Key_A)
        analysisMenu.addSeparator()
        analysisMenu.addAction('View 3D Morphometrics', self.viewMorphometrics, QtCore.Qt.Key_M)
        menuBar.addMenu(analysisMenu)

        helpMenu = QtWidgets.QMenu('&Help', stackWindow)
        helpMenu.addAction('&Shortcuts', self.showHotkeys, QtCore.Qt.Key_F1)
        helpMenu.addAction('View online documentation', self.openDocumentation)
        menuBar.addSeparator()
        menuBar.addMenu(helpMenu)

        self._updateForDrawMode()

    def _local(self):
        """Access to the stack window, for local operations that affect just this stack."""
        return self.stackWindow.actionHandler

    def _global(self):
        """Access to the dynamo window, for global operations that affect all stacks."""
        return self.stackWindow.parent()

    def _updateForDrawMode(self):
        inDrawMode = self._global().fullState.inDrawMode()
        for action in self.drawModeOnly:
            action.setEnabled(inDrawMode)
        inRegMode = self._global().fullState.inManualRegistrationMode
        for action in self.registerModeOnly:
            action.setEnabled(inRegMode)

    # File menu callbacks:
    def appendStack(self, *args):
        self._global().openFilesAndAppendStacks()

    def save(self):
        self._global().saveToFile()

    def saveAs(self):
        self._global().saveToNewFile()

    def importFromPreviousStack(self):
        self._local().importPointsFromLastStack(self.stackWindow.windowIndex)
        self.redraw()

    def importFromSWC(self):
        filePath = getOpenFileName(self.stackWindow,
            "Import SWC file", "", "SWC file (*.swc)"
        )
        if filePath is not None and filePath is not '':
            self._local().importPointsFromSWC(self.stackWindow.windowIndex, filePath)
            self.redraw()

    def exportToSWC(self):
        self._global().exportToSWC()

    def openSettings(self):
        self._global().openSettings()

    def closeWindow(self):
        self.stackWindow.close()

    def closeDynamo(self):
        self._global().quitAndMaybeSave()

    # Edit menu callbacks:
    def undo(self):
        self._global().updateUndoStack(isRedo=False, originWindow=self.stackWindow)

    def redo(self):
        self._global().updateUndoStack(isRedo=True, originWindow=self.stackWindow)

    def find(self):
        pointOrBranchID, okPressed = QtWidgets.QInputDialog.getText(self.stackWindow,
            "Find by ID", "Point or Branch ID:", QtWidgets.QLineEdit.Normal, "")
        if okPressed:
            self._global().findByID(pointOrBranchID)

    def annotateThis(self):
        self._global().fullActions.getAnnotation(
            self.stackWindow.windowIndex, self.stackWindow, False
        )
        self.redraw()

    def annotateAll(self):
        self._global().fullActions.getAnnotation(
            self.stackWindow.windowIndex, self.stackWindow, True
        )
        self._global().redrawAllStacks()

    def register(self):
        self._local().registerImages(self.stackWindow.windowIndex)
        self.redraw()

    def reparent(self):
        self._local().startReplaceParent()

    def primaryBranch(self):
        self._global().fullActions.setSelectedAsPrimaryBranch(self.stackWindow.windowIndex)
        self._global().redrawAllStacks()

    def allPrimaryBranches(self):
        self._global().updateAllPrimaryBranches(self.stackWindow)
        self._global().redrawAllStacks()

    def punctaMode(self):
        self._global().togglePunctaMode()
        self._updateForDrawMode()

    def manualRegister(self):
        self._global().toggleManualRegistration()
        self._updateForDrawMode()

    def alignIDsToFirst(self):
        if self._global().fullState.inManualRegistrationMode:
            self._global().fullActions.alignVisibleIDs(toNewID=False)
            self._global().redrawAllStacks()

    def alignIDsToNew(self):
        if self._global().fullState.inManualRegistrationMode:
            self._global().fullActions.alignVisibleIDs(toNewID=True)
            self._global().redrawAllStacks()

    def cyclePointModes(self):
        self._local().cyclePointModes()
        self._global().redrawAllStacks()

    # View menu callbacks:
    def zoomIn(self):
        self._local().zoom(-0.2) # ~= ln(0.8) as used in matlab

    def zoomOut(self):
        self._local().zoom(0.2)

    def view3DArbor(self):
        self._local().launch3DArbor()

    def view3DVolume(self):
        self._local().launch3DVolume()

    def toggleLineSize(self):
        self._global().fullState.toggleLineWidth()
        self._global().redrawAllStacks()

    def toggleDotSize(self):
        self._global().fullState.toggleDotSize()
        self._global().redrawAllStacks()

    def changeChannel(self):
        self._global().fullActions.nextChannel()
        self._global().redrawAllStacks()

    def toggleColor(self):
        self._global().fullState.useColor = not self._global().fullState.useColor
        self._global().redrawAllStacks()

    def cycleBranchDisplayMode(self):
        self.stackWindow.uiState.cycleBranchDisplayMode()
        self.redraw()

    def cyclePointInfo(self):
        self.stackWindow.uiState.cyclePointInfo()
        self.redraw()

    def toggleHilight(self):
        self.stackWindow.uiState.showHilighted = not self.stackWindow.uiState.showHilighted
        self.redraw()

    def toggleShowAll(self):
        self.stackWindow.uiState.hideAll = not self.stackWindow.uiState.hideAll
        self.redraw()

    def zProject(self):
        self._local().toggleZProjection()

    def tileFigs(self):
        self._global().focusFirstOpenStackWindow()
        tileFigs(self._global().stackWindows)

    # Analysis menu callbacks:
    def launchAnalysis(self):
        self._global().openAnalysisPopup()

    def viewMorphometrics(self):
        parent = self._global()
        opt = parent.fullState.projectOptions.motilityOptions
        Motility3DViewWindow(parent, self.stackWindow.windowIndex,
            parent.fullState.trees, parent.fullState.filePaths, opt).show()

    # Help menu callbacks:
    def showHotkeys(self):
        self._local().showHotkeys()

    def openDocumentation(self):
        webbrowser.open('http://padster.github.io/pyDynamo')

    # Misc:
    def redraw(self):
        self.stackWindow.redraw()
