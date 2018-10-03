from PyQt5 import QtCore, QtWidgets

from util.testableFilePicker import getOpenFileName

from .motility3DViewWindow import Motility3DViewWindow
from .tilefigs import tileFigs

class TopMenu():
    def __init__(self, stackWindow):
        self.stackWindow = stackWindow
        menuBar = stackWindow.menuBar()

        fileMenu = QtWidgets.QMenu('&File', stackWindow)
        fileMenu.addAction('&New stack...', self.appendStack, QtCore.Qt.Key_N)
        fileMenu.addAction('&Save', self.save, QtCore.Qt.CTRL + QtCore.Qt.Key_S)
        fileMenu.addAction('Save As...', self.saveAs, QtCore.Qt.CTRL + QtCore.Qt.SHIFT + QtCore.Qt.Key_S)
        fileMenu.addSeparator()
        fileMenu.addAction('Import from previous stack', self.importFromPreviousStack, QtCore.Qt.Key_I)
        fileMenu.addAction('Import from SWC...', self.importFromSWC, QtCore.Qt.CTRL + QtCore.Qt.Key_I)
        fileMenu.addAction('Export to SWC...', self.exportToSWC, QtCore.Qt.CTRL + QtCore.Qt.Key_E)
        fileMenu.addSeparator()
        fileMenu.addAction('&Project Settings...', self.openSettings, QtCore.Qt.CTRL + QtCore.Qt.SHIFT + QtCore.Qt.Key_P)
        fileMenu.addAction('Close &Window', self.closeWindow, QtCore.Qt.CTRL + QtCore.Qt.Key_W)
        fileMenu.addAction('Close Dynamo', self.closeDynamo, QtCore.Qt.CTRL + QtCore.Qt.SHIFT + QtCore.Qt.Key_W)
        menuBar.addMenu(fileMenu)

        editMenu = QtWidgets.QMenu('&Edit', stackWindow)
        editMenu.addAction('Undo', self.undo, QtCore.Qt.CTRL + QtCore.Qt.Key_Z)
        editMenu.addAction('Redo', self.redo, QtCore.Qt.CTRL + QtCore.Qt.SHIFT + QtCore.Qt.Key_Z)
        editMenu.addSeparator()
        editMenu.addAction('Find', self.find, QtCore.Qt.CTRL + QtCore.Qt.Key_F)
        editMenu.addSeparator()
        editMenu.addAction('Register from previous stack', self.register, QtCore.Qt.Key_R)
        editMenu.addAction('&Replace parent', self.reparent, QtCore.Qt.CTRL + QtCore.Qt.Key_R)
        menuBar.addMenu(editMenu)

        viewMenu = QtWidgets.QMenu('&View', stackWindow)
        viewMenu.addAction('Zoom In', self.zoomIn, QtCore.Qt.Key_X)
        viewMenu.addAction('Zoom Out', self.zoomOut, QtCore.Qt.Key_Z)
        viewMenu.addSeparator()
        viewMenu.addAction('View 3D Neuron', self.view3D, QtCore.Qt.Key_3)
        viewMenu.addAction('View 3D Morphometrics', self.viewMorphometrics, QtCore.Qt.Key_M)
        viewMenu.addSeparator()
        viewMenu.addAction('Toggle line size', self.toggleLineSize, QtCore.Qt.Key_J)
        viewMenu.addAction('Toggle dot size', self.toggleDotSize, QtCore.Qt.SHIFT + QtCore.Qt.Key_J)
        viewMenu.addAction('Change channel', self.changeChannel, QtCore.Qt.Key_C)
        viewMenu.addAction('Turn on/off colours', self.toggleColor, QtCore.Qt.SHIFT + QtCore.Qt.Key_C)
        viewMenu.addAction('Show/Hide all branches', self.toggleAllBranches, QtCore.Qt.Key_V)
        viewMenu.addAction('Show/Hide hilighted points', self.toggleHilight, QtCore.Qt.Key_H)
        viewMenu.addAction('Show/Hide entire tree', self.toggleShowAll, QtCore.Qt.SHIFT + QtCore.Qt.Key_H)
        viewMenu.addAction('Project all Z onto one image', self.zProject, QtCore.Qt.Key_Underscore)
        viewMenu.addAction('Tile windows on screen', self.tileFigs, QtCore.Qt.Key_T)
        menuBar.addMenu(viewMenu)

        helpMenu = QtWidgets.QMenu('&Help', stackWindow)
        menuBar.addSeparator()
        menuBar.addMenu(helpMenu)
        helpMenu.addAction('&Shortcuts', self.showHotkeys, QtCore.Qt.Key_F1)

    def _local(self):
        """Access to the stack window, for local operations that affect just this stack."""
        return self.stackWindow.actionHandler

    def _global(self):
        """Access to the dynamo window, for global operations that affect all stacks."""
        return self.stackWindow.parent()

    # File menu callbacks:
    def appendStack(self):
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
        self._global().quit()

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

    def register(self):
        self._local().registerImages(self.stackWindow.windowIndex)
        self.redraw()

    def reparent(self):
        self._local().startReplaceParent()

    # View menu callbacks:
    def zoomIn(self):
        self._local().zoom(-0.2) # ~= ln(0.8) as used in matlab

    def zoomOut(self):
        self._local().zoom(0.2)

    def view3D(self):
        self._local().launch3DView()

    def viewMorphometrics(self):
        parent = self._global()
        opt = parent.fullState.projectOptions.motilityOptions
        Motility3DViewWindow(parent, self.stackWindow.windowIndex,
            parent.fullState.trees, parent.fullState.filePaths, opt).show()

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

    def toggleAllBranches(self):
        self.stackWindow.uiState.drawAllBranches = not self.stackWindow.uiState.drawAllBranches
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


    # Help menu callbacks:
    def showHotkeys(self):
        self._local().showHotkeys()

    # Misc:
    def redraw(self):
        self.stackWindow.redraw()
