from PyQt5.QtCore import QRectF
from PyQt5.QtWidgets import QApplication, QWidget, QInputDialog, QLineEdit

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

    def regsiterImage(self, windowIndex):
        if windowIndex == 0:
            print ("Can't register the first image, nothing to register it against...")
            return
        recursiveAdjust
