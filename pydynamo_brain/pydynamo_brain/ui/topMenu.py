from PyQt5 import QtCore, QtWidgets

import webbrowser

from pydynamo_brain.model import DrawMode
from pydynamo_brain.util.testableFilePicker import getOpenFileName

from .common import createAndShowInfo
from .motility.motility3DViewWindow import Motility3DViewWindow
from .registration.registration3DViewWindow import Registration3DViewWindow
from .sholl.shollViewWindow import ShollViewWindow
from .tree3D.tree3DViewWindow import Tree3DViewWindow
from .tilefigs import tileFigs

class TopMenu():
    def __init__(self, stackWindow):
        self.stackWindow = stackWindow
        menuBar = stackWindow.menuBar()

        # Map {action: list of modes they are enabled in}
        # Any action not in the map is always enabled
        self.modeRestrictedActions = {}
        dmo    = lambda x: self.modeRestrictedActions.update({x: [DrawMode.DEFAULT]})
        rmo    = lambda x: self.modeRestrictedActions.update({x: [DrawMode.REGISTRATION]})
        radii  = lambda x: self.modeRestrictedActions.update({x: [DrawMode.RADII]})
        doramo = lambda x: self.modeRestrictedActions.update({x: [DrawMode.DEFAULT, DrawMode.RADII]})

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

        dmo(editMenu.addAction('&Replace parent', self.reparent, QtCore.Qt.CTRL + QtCore.Qt.Key_R))
        dmo(editMenu.addAction('Set as primary &branch', self.primaryBranch, QtCore.Qt.CTRL + QtCore.Qt.Key_B))
        dmo(editMenu.addAction('Clean up all primary &branches in all stacks',
            self.allPrimaryBranches, QtCore.Qt.CTRL + QtCore.Qt.SHIFT + QtCore.Qt.Key_B))
        dmo(editMenu.addAction('Clean branch &IDs from first point in all stacks',
            self.cleanBranchIDs, QtCore.Qt.CTRL + QtCore.Qt.SHIFT + QtCore.Qt.Key_I))
        dmo(editMenu.addAction('Remove empty branches from all stacks',
            self.cleanEmptyBranches, QtCore.Qt.SHIFT + QtCore.Qt.Key_E))
        editMenu.addAction('Draw &Puncta', self.punctaMode, QtCore.Qt.Key_P)
        editMenu.addAction('Draw Radii', self.radiiMode, QtCore.Qt.ALT + QtCore.Qt.Key_R)
        doramo(editMenu.addAction('Cycle select->move->reparent modes', self.cyclePointModes, QtCore.Qt.Key_Tab))

        manualRegisterSubmenu = editMenu.addMenu("Registration")
        manualRegisterSubmenu.addAction('View point registration', self.viewRegistration, QtCore.Qt.SHIFT + QtCore.Qt.Key_R)
        dmo(manualRegisterSubmenu.addAction("Register and move from previous stack's volume",
            self.registerSmart, QtCore.Qt.Key_R))
        dmo(manualRegisterSubmenu.addAction("Register IDs from previous stack's tree (no movement)",
            self.registerIDs, QtCore.Qt.SHIFT + QtCore.Qt.Key_F))
        manualRegisterSubmenu.addSeparator()
        manualRegisterSubmenu.addAction('Start/end manual registration',
            self.manualRegister, QtCore.Qt.CTRL + QtCore.Qt.SHIFT + QtCore.Qt.Key_R)
        rmo(manualRegisterSubmenu.addAction(' -> Manual: Align IDs all selected points',
            self.alignIDsToFirst, QtCore.Qt.SHIFT + QtCore.Qt.Key_Return))
        rmo(manualRegisterSubmenu.addAction(' -> Manual: Assign a new ID to all selected points',
            self.alignIDsToNew, QtCore.Qt.SHIFT + QtCore.Qt.Key_Apostrophe))
        menuBar.addMenu(editMenu)

        manualRadiiSubmenu = editMenu.addMenu("Radii Mode")
        radii(manualRadiiSubmenu.addAction("Recursive Radii Estimation", self.radiiEstimator, QtCore.Qt.SHIFT + QtCore.Qt.Key_G))
        radii(manualRadiiSubmenu.addAction("Single Radius Estimation", self.singleRadiusEstimator, QtCore.Qt.Key_G))

        viewMenu = QtWidgets.QMenu('&View', stackWindow)
        viewMenu.addAction('Zoom In', self.zoomIn, QtCore.Qt.Key_X)
        viewMenu.addAction('Zoom Out', self.zoomOut, QtCore.Qt.Key_Z)
        viewMenu.addAction('View 3D Arbor', self.view3DArbor, QtCore.Qt.CTRL + QtCore.Qt.Key_3)
        viewMenu.addAction('View 3D Arbor (old)', self.view3DArborOld, QtCore.Qt.Key_3)
        viewMenu.addAction('View 3D Image Volume', self.view3DVolume, QtCore.Qt.SHIFT + QtCore.Qt.Key_3)

        viewMenu.addSeparator()
        doramo(viewMenu.addAction('Toggle line size', self.toggleLineSize, QtCore.Qt.Key_J))
        doramo(viewMenu.addAction('Toggle dot size', self.toggleDotSize, QtCore.Qt.SHIFT + QtCore.Qt.Key_J))
        viewMenu.addAction('Change channel', self.changeChannel, QtCore.Qt.Key_C)
        viewMenu.addAction('Turn on/off colours', self.toggleColor, QtCore.Qt.SHIFT + QtCore.Qt.Key_C)
        viewMenu.addAction('Cycle showing branches on this Z -> nearby Z -> all Z',
            self.cycleBranchDisplayMode, QtCore.Qt.Key_V)
        viewMenu.addAction('Cycle showing annotations -> IDs -> nothing per point', self.cyclePointInfo, QtCore.Qt.Key_F)
        dmo(viewMenu.addAction('Show/Hide marked points', self.toggleMarked, QtCore.Qt.Key_H))
        viewMenu.addAction('Show/Hide entire tree', self.toggleShowAll, QtCore.Qt.SHIFT + QtCore.Qt.Key_H)
        viewMenu.addAction('Project all Z onto one image', self.zProject, QtCore.Qt.Key_Underscore)
        viewMenu.addAction('Mark downstream points on selected window', self.markPoints, QtCore.Qt.SHIFT + QtCore.Qt.Key_M)
        viewMenu.addAction('Clear all marking of points', self.unmarkPoints, QtCore.Qt.CTRL + QtCore.Qt.SHIFT + QtCore.Qt.Key_M)
        viewMenu.addAction('Tile windows on screen', self.tileFigs, QtCore.Qt.Key_T)
        menuBar.addMenu(viewMenu)

        analysisMenu = QtWidgets.QMenu('&Analysis', stackWindow)
        analysisMenu.addAction('Perform data checks', self.performChecks)
        analysisMenu.addAction('Launch export window', self.launchAnalysis, QtCore.Qt.CTRL + QtCore.Qt.SHIFT + QtCore.Qt.Key_A)
        analysisMenu.addSeparator()

        inAppAnalysisSubmenu = analysisMenu.addMenu("Visualization")
        inAppAnalysisSubmenu.addAction('3D Morphometrics', lambda: self.viewMorphometrics(False), QtCore.Qt.Key_M)
        inAppAnalysisSubmenu.addAction('2D Morphometrics dendrograms', lambda: self.viewMorphometrics(True))
        inAppAnalysisSubmenu.addAction('Sholl graphs', self.viewSholl)

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
        mode = self._global().fullState.drawMode
        for action, enabledModes in self.modeRestrictedActions.items():
            action.setEnabled(mode in enabledModes)

    # File menu callbacks:
    def appendStack(self, *args):
        self._global().openFilesAndAppendStacks()

    def save(self):
        self._global().saveToFile(parentWindow=self.stackWindow)

    def saveAs(self):
        self._global().saveToNewFile(parentWindow=self.stackWindow)

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
        self._global().exportToSWC(parentWindow=self.stackWindow)

    def openSettings(self):
        self._global().openSettings()

    def closeWindow(self):
        self.stackWindow.close()

    def closeDynamo(self):
        self._global().quitAndMaybeSave(parentWindow=self.stackWindow)

    # Edit menu callbacks:
    def undo(self):
        self._global().updateUndoStack(isRedo=False, originWindow=self.stackWindow)

    def redo(self):
        self._global().updateUndoStack(isRedo=True, originWindow=self.stackWindow)

    def find(self):
        pointOrBranchID, okPressed = QtWidgets.QInputDialog.getText(self.stackWindow,
            "Find by ID", "Point or Branch ID:", QtWidgets.QLineEdit.Normal, "")
        if okPressed:
            self._global().findByID(pointOrBranchID, self.stackWindow)

    def annotateThis(self):
        self._global().fullActions.getAnnotation(
            self.stackWindow.windowIndex, self.stackWindow, False
        )
        self.redraw()

    def annotateAll(self):
        self._global().fullActions.getAnnotation(
            self.stackWindow.windowIndex, self.stackWindow, True
        )
        self._global().redrawAllStacks(self.stackWindow)

    def registerSmart(self):
        if self._global().fullState.inManualRegistrationMode():
            return
        self._local().smartRegisterImages(self.stackWindow.windowIndex)
        self.redraw()

    def radiiEstimator(self):
        if self._global().fullState.inRadiiMode:
            self._local().radiiEstimator(self.stackWindow.windowIndex)
            self.redraw()

    def singleRadiusEstimator(self):
        if self._global().fullState.inRadiiMode:
            self._local().singleRadiusEstimator(self.stackWindow.windowIndex)
            self.redraw()

    def registerIDs(self):
        if self._global().fullState.inManualRegistrationMode():
            return
        self._local().simpleRegisterImages(self.stackWindow.windowIndex)
        self.redraw()

    def reparent(self):
        self._local().startReplaceParent()

    def primaryBranch(self):
        self._global().fullActions.setSelectedAsPrimaryBranch(self.stackWindow.windowIndex)
        self._global().redrawAllStacks(self.stackWindow)

    def allPrimaryBranches(self):
        self._global().updateAllPrimaryBranches(self.stackWindow)
        self._global().redrawAllStacks(self.stackWindow)

    def cleanBranchIDs(self):
        self._global().fullActions.cleanBranchIDs()
        self._global().redrawAllStacks(self.stackWindow)

    def cleanEmptyBranches(self):
        self._global().cleanEmptyBranches(self.stackWindow)
        self._global().redrawAllStacks(self.stackWindow)

    def punctaMode(self):
        self._global().togglePunctaMode(self.stackWindow)
        self._updateForDrawMode()

    def radiiMode(self):
        self._global().toggleRadiiMode(self.stackWindow)
        self._updateForDrawMode()

    def manualRegister(self):
        self._global().toggleManualRegistration(self.stackWindow)
        self._updateForDrawMode()

    def alignIDsToFirst(self):
        if self._global().fullState.inManualRegistrationMode():
            self._global().fullActions.alignVisibleIDs(toNewID=False)
            self._global().redrawAllStacks(self.stackWindow)

    def alignIDsToNew(self):
        if self._global().fullState.inManualRegistrationMode():
            self._global().fullActions.alignVisibleIDs(toNewID=True)
            self._global().redrawAllStacks(self.stackWindow)

    def cyclePointModes(self):
        self._local().cyclePointModes()
        self._global().redrawAllStacks(self.stackWindow)

    # View menu callbacks:
    def zoomIn(self):
        self._local().zoom(-0.2) # ~= ln(0.8) as used in matlab

    def zoomOut(self):
        self._local().zoom(0.2)

    # TODO: remove when #trees for the new mode is configured in settings.
    def view3DArborOld(self):
        self._local().launch3DArbor()

    def view3DArbor(self):
        parent = self._global()
        if len(parent.fullState.trees) == 0:
            print ("Need at least one tree for 3D arbor view")
            return

        infoBox = createAndShowInfo("Drawing 3D trees...", self.stackWindow)
        Tree3DViewWindow(parent, parent.fullState, self.stackWindow.windowIndex,
            parent.fullState.trees, parent.fullState.filePaths).show()
        infoBox.hide()

    def view3DVolume(self):
        self._local().launch3DVolume()

    def toggleLineSize(self):
        self._global().fullState.toggleLineWidth()
        self._global().redrawAllStacks(self.stackWindow)

    def toggleDotSize(self):
        self._global().fullState.toggleDotSize()
        self._global().redrawAllStacks(self.stackWindow)

    def changeChannel(self):
        self._global().fullActions.nextChannel()
        self._global().redrawAllStacks(self.stackWindow)

    def toggleColor(self):
        self._global().fullState.useColor = not self._global().fullState.useColor
        self._global().redrawAllStacks(self.stackWindow)

    def cycleBranchDisplayMode(self):
        self.stackWindow.uiState.cycleBranchDisplayMode()
        self.redraw()

    def cyclePointInfo(self):
        self.stackWindow.uiState.cyclePointInfo()
        self.redraw()

    def toggleMarked(self):
        self.stackWindow.uiState.showMarked = not self.stackWindow.uiState.showMarked
        self.redraw()

    def toggleShowAll(self):
        self.stackWindow.uiState.hideAll = not self.stackWindow.uiState.hideAll
        self.redraw()

    def zProject(self):
        self._local().toggleZProjection()

    def markPoints(self):
        self._local().markPoints()

    def unmarkPoints(self):
        self._local().unmarkPoints()

    def tileFigs(self):
        self._global().focusFirstOpenStackWindow()
        tileFigs(self._global().stackWindows)

    # Analysis menu callbacks:
    def performChecks(self):
        self._local().performChecks()

    def launchAnalysis(self):
        self._global().openAnalysisPopup()

    def viewMorphometrics(self, is2D):
        parent = self._global()
        if len(parent.fullState.trees) <= 1:
            print ("Need >= 2 trees for morphometrics display")
            return

        infoBox = createAndShowInfo("Calculating Motility...", self.stackWindow)
        opt = parent.fullState.projectOptions.motilityOptions
        Motility3DViewWindow(parent, self.stackWindow.windowIndex,
            parent.fullState.trees, is2D, parent.fullState.filePaths, opt).show()
        infoBox.hide()

    def viewRegistration(self):
        parent = self._global()
        if len(parent.fullState.trees) <= 1:
            print ("Need >= 2 trees for registration display")
            return
        infoBox = createAndShowInfo("Calculating Registration...", self.stackWindow)
        Registration3DViewWindow(parent, self.stackWindow.windowIndex,
            parent.fullState.trees, parent.fullState.filePaths).show()
        infoBox.hide()

    def viewSholl(self):
        parent = self._global()
        if len(parent.fullState.trees) == 0:
            print ("Need at least one tree for Sholl display")
            return

        infoBox = createAndShowInfo("Calculating Sholl...", self.stackWindow)
        ShollViewWindow(parent, parent.fullState, self.stackWindow.windowIndex,
            parent.fullState.trees, parent.fullState.filePaths).show()
        infoBox.hide()

    # Help menu callbacks:
    def showHotkeys(self):
        self._local().showHotkeys()

    def openDocumentation(self):
        webbrowser.open('http://padster.github.io/pyDynamo')

    # Misc:
    def redraw(self):
        self.stackWindow.redraw()
