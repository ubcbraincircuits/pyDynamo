from PyQt5.QtCore import QRectF
from PyQt5.QtWidgets import QApplication, QWidget, QInputDialog, QLineEdit, QMessageBox

import util
from ..dendrite3DViewWindow import Dendrite3DViewWindow
from ..helpDialog import showHelpDialog

from model import recursiveAdjust

class DendriteCanvasActions():
    COLOR_SENSITIVITY = 10.0 / 256.0

    def __init__(self, dendriteCanvas, imagePath, treeModel, uiState):
        self.canvas = dendriteCanvas
        self.imagePath = imagePath
        self.treeModel = treeModel
        self.uiState = uiState

    def updateUIState(self, newUiState):
        self.uiState = newUiState

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

    def getAnnotation(self, window):
        currentPoint = self.uiState.currentPoint()
        text, okPressed = QInputDialog.getText(window,
            "Annotate point", "Enter annotation:", QLineEdit.Normal, currentPoint.annotation)
        if okPressed:
            currentPoint.annotation = text

    def showHotkeys(self):
        showHelpDialog()

    def launch3DView(self):
        viewWindow = Dendrite3DViewWindow(self.canvas.parent(), self.imagePath, self.treeModel)
        viewWindow.show()

    def importPoints(self, windowIndex):
        if windowIndex == 0:
            print ("Can't import points into the first image, nothing to import from...")
        thisTree = self.uiState.parent().trees[windowIndex]
        lastTree = self.uiState.parent().trees[windowIndex - 1]
        assert thisTree is not None and lastTree is not None
        thisTree.clearAndCopyFrom(lastTree)

    def registerImages(self, windowIndex):
        if windowIndex == 0:
            print ("Can't register the first image, nothing to register it against...")
            return

        pointNew, pointOld, branch = None, None, None
        # Use selected point if one is
        if self.uiState.currentPointID is not None:
            pointNew = self.uiState.parent().trees[windowIndex  ].getPointByID(
                self.uiState.parent().uiStates[windowIndex  ].currentPointID)
            pointOld = self.uiState.parent().trees[windowIndex-1].getPointByID(
                self.uiState.parent().uiStates[windowIndex-1].currentPointID)
            branch = pointNew.parentBranch
        # Default to root if anything is wrong...
        if pointNew is None or pointOld is None or branch is None:
            branch = None
            pointNew = self.uiState.parent().trees[windowIndex].rootPoint
            pointOld = self.uiState.parent().trees[windowIndex-1].rootPoint

        # Un-hilight old points
        for p in self.uiState.parent().trees[windowIndex].flattenPoints():
            p.hilighted = False

        self.canvas.stackWindow.statusBar().showMessage("Registering...")
        self.canvas.stackWindow.repaint()
        recursiveAdjust(self.uiState.parent(), windowIndex, branch, pointNew, pointOld)
        self.uiState.showHilighted = True
        self.canvas.redraw()
        msg = QMessageBox(QMessageBox.Information, "Registration",
            "Registration complete! Unregistered points shown in green, press 'h' to toggle hilight.", parent=self.canvas)
        msg.show()
        self.canvas.stackWindow.statusBar().clearMessage()
        # self.canvas.stackWindow.repaint()
