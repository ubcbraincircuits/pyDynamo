from PyQt5.QtCore import QRectF
from PyQt5.QtWidgets import QApplication, QWidget, QInputDialog, QLineEdit, QMessageBox

import util
from ..dendrite3DViewWindow import Dendrite3DViewWindow
from ..helpDialog import showHelpDialog

from files import importFromSWC
from model import recursiveAdjust

class DendriteCanvasActions():
    COLOR_SENSITIVITY = 10.0 / 256.0

    def __init__(self, windowIndex, fullActions, uiState, dendriteCanvas, imagePath):
        self.windowIndex = windowIndex
        self.fullActions = fullActions
        self.uiState = uiState
        self.canvas = dendriteCanvas
        self.imagePath = imagePath

    def updateUIState(self, newUiState):
        self.uiState = newUiState

    def updateWindowIndex(self, windowIndex):
        self.windowIndex = windowIndex

    def zoom(self, logAmount):
        self.canvas.imgView.zoom(logAmount)

    def pan(self, xDelta, yDelta):
        outsideRect = self.canvas.imgView.sceneRect()
        viewBox = self.canvas.imgView.getViewportRect()
        xDeltaPx = util.snapToRange(
            (int)(xDelta * viewBox.width() * 0.1),
            outsideRect.left() - viewBox.left(),
            outsideRect.right() - viewBox.right()
        )
        yDeltaPx = util.snapToRange(
            (int)(yDelta * viewBox.height() * 0.1),
            outsideRect.top() - viewBox.top(),
            outsideRect.bottom() - viewBox.bottom()
        )
        viewBox.translate(xDeltaPx, yDeltaPx)
        viewBox = viewBox.intersected(self.canvas.imgView.sceneRect())
        self.canvas.imgView.moveViewRect(viewBox)

    def changeBrightness(self, lower, upper, reset=False):
        if reset:
            self.uiState.colorLimits = (0, 1)
        else:
            self.uiState.changeBrightness(lower * self.COLOR_SENSITIVITY, upper * self.COLOR_SENSITIVITY)
        self.canvas.redraw()

    def showHotkeys(self):
        showHelpDialog()

    def toggleZProjection(self):
        self.uiState.zProject = not self.uiState.zProject
        self.canvas.redraw()

    def launch3DView(self):
        viewWindow = Dendrite3DViewWindow(self.canvas.parent(), self.imagePath, self.uiState._tree)
        viewWindow.show()

    def importPointsFromLastStack(self, windowIndex):
        if windowIndex == 0:
            print ("Can't import points into the first image, nothing to import from...")
            return
        thisTree = self.uiState.parent().trees[windowIndex]
        lastTree = self.uiState.parent().trees[windowIndex - 1]
        assert thisTree is not None and lastTree is not None
        thisTree.clearAndCopyFrom(lastTree, None) # No id maker, so clone IDs

    def importPointsFromSWC(self, windowIndex, filePath):
        thisTree = self.uiState.parent().trees[windowIndex]
        if thisTree is None or thisTree.rootPoint is not None:
            print ("Arbor has points already, please only run on an empty image.")
            return
        newTree = importFromSWC(filePath)
        if newTree is not None:
            thisTree.clearAndCopyFrom(newTree, self.uiState.parent())

    def registerImages(self, windowIndex):
        if windowIndex == 0:
            print ("Can't register the first image, nothing to register it against...")
            return

        pointNew = self.uiState.currentPoint()
        pointOld = self.uiState.parent().uiStates[windowIndex-1].currentPoint()
        branch = None if pointNew is None else pointNew.parentBranch

        # Default to root if anything is wrong...
        if pointNew is None or pointOld is None or branch is None:
            branch = None
            pointNew = self.uiState.parent().trees[windowIndex].rootPoint
            pointOld = self.uiState.parent().trees[windowIndex-1].rootPoint

        # Un-hilight old points
        allSubtreePoints = pointNew.flattenSubtreePoints()
        pointCount = len(allSubtreePoints)
        for p in allSubtreePoints:
            p.hilighted = False

        # Progress bar! Note: array here as it's edited inside the callback.
        pointAt = [0]
        self.canvas.stackWindow.statusBar().showMessage(
            "Registering...  %d/%d points processed." % (pointAt[0], pointCount))
        self.canvas.stackWindow.repaint()
        def progressUpdate(pointsProcessed):
            pointAt[0] += pointsProcessed
            self.canvas.stackWindow.statusBar().showMessage(
                "Registering...  %d/%d points processed." % (pointAt[0], pointCount))

        recursiveAdjust(self.uiState.parent(), windowIndex, branch, pointNew, pointOld, progressUpdate)
        self.uiState.showHilighted = True
        self.canvas.redraw()
        msg = QMessageBox(QMessageBox.Information, "Registration",
            "Registration complete! Unregistered points shown in green, press 'h' to toggle hilight.", parent=self.canvas)
        msg.show()
        self.canvas.stackWindow.statusBar().clearMessage()

    def startReplaceParent(self):
        self.uiState.isReparenting = True
        self.canvas.redraw()

    def stopReplaceParent(self):
        self.uiState.isReparenting = False
        self.canvas.redraw()

    # Cycle selection -> Moving -> Reparenting -> back
    def cyclePointModes(self):
        currentPoint = self.uiState.currentPoint()
        if currentPoint is not None:
            if self.uiState.isMoving:
                # Moving -> Reparenting
                self.fullActions.cancelMove()
                self.startReplaceParent()
            elif self.uiState.isReparenting:
                # Reparenting -> Selection
                self.stopReplaceParent()
            else:
                # Selection -> Moving
                self.fullActions.beginMove(self.windowIndex, currentPoint)
