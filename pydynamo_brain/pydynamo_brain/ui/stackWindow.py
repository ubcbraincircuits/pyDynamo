import math
import numpy as np
import traceback

from PyQt5 import QtCore, QtWidgets

import pydynamo_brain.files as files
import pydynamo_brain.util as util

from .actions.dendriteCanvasActions import DendriteCanvasActions
from .dendriteVolumeCanvas import DendriteVolumeCanvas
from .np2qt import np2qt
from .QtImageViewer import QtImageViewer
from .topMenu import TopMenu

_IMG_CACHE = util.ImageCache()

class StackWindow(QtWidgets.QMainWindow):
    def __init__(self, windowIndex, imagePath, fullActions, uiState, parent):
        QtWidgets.QMainWindow.__init__(self, parent)

        assert not uiState.isHidden # Only have windows attached to shown states.

        self.windowIndex = windowIndex
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowMinMaxButtonsHint)

        assert imagePath is not None
        self.imagePath = imagePath
        uiState.imagePath = imagePath
        _IMG_CACHE.handleNewUIState(uiState)

        self.windowIndex = windowIndex
        self.updateTitle()

        self.root = QtWidgets.QWidget(self)
        self.dendrites = DendriteVolumeCanvas(
            windowIndex, fullActions, uiState, parent, self, self.root
        )
        self.actionHandler = DendriteCanvasActions(
            windowIndex, fullActions, uiState, self.dendrites, imagePath
        )
        self.fullActions = fullActions
        self.uiState = uiState
        self.ignoreUndoCloseEvent = False

        # Assemble the view hierarchy.
        l = QtWidgets.QGridLayout(self.root)
        l.setContentsMargins(0, 0, 0, 0)
        l.addWidget(self.dendrites, 0, 0)
        self.root.setFocus()
        self.setCentralWidget(self.root)

        # Top level menu:
        self.topMenu = TopMenu(self)
        self.statusBar().showMessage("") # Force it to be visible, so we can use later.

    def closeEvent(self, event):
        if not self.ignoreUndoCloseEvent:
            self.parent().removeStackWindow(self.windowIndex)

    def updateState(self, newFilePath, newUiState):
        assert not newUiState.isHidden # Only have windows attached to shown states.
        self.imagePath = newFilePath
        self.uiState = newUiState
        self.dendrites.updateState(newUiState)
        self.actionHandler.updateUIState(newUiState)
        _IMG_CACHE.handleNewUIState(newUiState)
        self.updateTitle()

    def updateWindowIndex(self, windowIndex):
        self.windowIndex = windowIndex
        self.dendrites.updateWindowIndex(windowIndex)
        self.actionHandler.updateWindowIndex(windowIndex)
        self.updateTitle()

    def updateTitle(self):
        self.setWindowTitle(util.createTitle(self.windowIndex, self.imagePath))

    def redraw(self):
        self.dendrites.redraw()

    # Get the current x,y position of the selected point
    def getSelectionLocation(self):
        pointAt = self.uiState.currentPoint()
        return None if pointAt is None else pointAt.location

    # Move the current viewport so the selected point is at the given x, y
    def updateSelectionLocation(self, oldLocation):
        pointAt = self.uiState.currentPoint()
        if pointAt is None:
            return None
        dX = pointAt.location[0] - oldLocation[0]
        dY = pointAt.location[1] - oldLocation[1]
        # Translate it locally to fix the selected point
        self.dendrites.imgView.onlyPerformLocalViewRect = True
        self.dendrites.imgView.moveViewRect(
            self.dendrites.imgView.getViewportRect().translated(dX, dY))
        self.dendrites.imgView.onlyPerformLocalViewRect = False

    def doMove(self, dX, dY, downstream, laterStacks):
        MOVE_FACTOR = 0.05 # 1/20 of screen per button press
        xScale, yScale = self.dendrites.imgView.sceneDimension()
        scale = min(xScale, yScale)
        dX = dX * scale * MOVE_FACTOR
        dY = dY * scale * MOVE_FACTOR
        self.fullActions.doMove(self.windowIndex, dX, dY, downstream, laterStacks)
        if laterStacks:
            self.parent().redrawAllStacks()
        else:
            self.dendrites.redraw()

    def doPunctaMove(self, dX, dY, laterStacks):
        MOVE_FACTOR = 0.05 # 1/20 of screen per button press
        xScale, yScale = self.dendrites.imgView.sceneDimension()
        scale = min(xScale, yScale)
        dX = dX * scale * MOVE_FACTOR
        dY = dY * scale * MOVE_FACTOR
        self.fullActions.punctaActions.relativeMove(self.windowIndex, dX, dY, laterStacks)
        if laterStacks:
            self.parent().redrawAllStacks()
        else:
            self.dendrites.redraw()

    def doPunctaGrow(self, dR, laterStacks):
        self.fullActions.punctaActions.relativeGrow(self.windowIndex, dR, laterStacks)
        if laterStacks:
            self.parent().redrawAllStacks()
        else:
            self.dendrites.redraw()

    def keyPressEvent(self, event):
        try:
            if self.parent().childKeyPress(event, self):
                return
            altsPressed = (event.modifiers() & QtCore.Qt.AltModifier)
            ctrlPressed = (event.modifiers() & QtCore.Qt.ControlModifier)
            shftPressed = (event.modifiers() & QtCore.Qt.ShiftModifier)

            # Actions here all apply even if the stack's tree is hidden:
            key = event.key()
            if (key == ord('4')):
                self.actionHandler.changeBrightness(-1, 0)
            elif (key == ord('5')):
                self.actionHandler.changeBrightness(1, 0)
            elif (key == ord('6')):
                self.actionHandler.changeBrightness(0, 0, reset=True)
            elif (key == ord('7')):
                self.actionHandler.changeBrightness(0, -1)
            elif (key == ord('8')):
                self.actionHandler.changeBrightness(0, 1)
            elif (key == ord('W')):
                if self.uiState.isMoving:
                    self.doMove(0, -1, shftPressed, altsPressed)
                elif self.uiState._parent.inPunctaMode:
                    self.doPunctaMove(0, -1, altsPressed)
                else:
                    self.actionHandler.pan(0, -1)
            elif (key == ord('A')):
                if self.uiState.isMoving:
                    self.doMove(-1, 0, shftPressed, altsPressed)
                elif self.uiState._parent.inPunctaMode:
                    self.doPunctaMove(-1, 0, altsPressed)
                else:
                    self.actionHandler.pan(-1, 0)
            elif (key == ord('S')):
                if self.uiState.isMoving:
                    self.doMove(0, 1, shftPressed, altsPressed)
                elif self.uiState._parent.inPunctaMode:
                    self.doPunctaMove(0, 1, altsPressed)
                else:
                    self.actionHandler.pan(0, 1)
            elif (key == ord('D')):
                if self.uiState.isMoving:
                    self.doMove(1, 0, shftPressed, altsPressed)
                elif self.uiState._parent.inPunctaMode:
                    self.doPunctaMove(1, 0, altsPressed)
                else:
                    self.actionHandler.pan(1, 0)
            elif (key == ord('Q')):
                if self.uiState._parent.inPunctaMode:
                    self.doPunctaGrow(1.0 / 0.9, altsPressed)
            elif (key == ord('E')):
                if self.uiState._parent.inPunctaMode:
                    self.doPunctaGrow(0.9, altsPressed)

            if self.uiState.hideAll:
                return
            # Actions only apply if the stack's tree is visible start below.

            # Actions that apply in manual registration mode (and others)
            if key == ord('<') or key == ord('>'):
                # Prev / Next in branch selector
                delta = -1 if key == ord('<') else 1
                if self.uiState._parent.inPunctaMode:
                    self.fullActions.punctaActions.selectNextPoint(self.windowIndex, delta)
                else:
                    locationSnapshot = self.parent().snapshotSelectionLocation()
                    self.fullActions.selectNextPoints(delta)
                    self.parent().updateSelectionLocation(locationSnapshot)

                self.parent().redrawAllStacks()
            elif key == ord('?'):
                # First child of current point selector
                if not self.uiState._parent.inPunctaMode:
                    locationSnapshot = self.parent().snapshotSelectionLocation()
                    self.fullActions.selectFirstChildren()
                    self.parent().updateSelectionLocation(locationSnapshot)
                    self.parent().redrawAllStacks()

            if self.uiState._parent.inManualRegistrationMode:
                return
            if self.uiState._parent.inPunctaMode:
                return

            elif key == QtCore.Qt.Key_Delete:
                toDelete = self.uiState.currentPoint()
                if toDelete is None:
                    print ("Need to select a point before you can delete...")
                else:
                    self.fullActions.deletePoint(self.windowIndex, toDelete, laterStacks=shftPressed)
                    self.parent().redrawAllStacks() # HACK - auto redraw on change

        except Exception as e:
            print ("Whoops - error on keypress: " + str(e))
            traceback.print_exc()
            # TODO: add this back in if the app feels stable?
            # raise
