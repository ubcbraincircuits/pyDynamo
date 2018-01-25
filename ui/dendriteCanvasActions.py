from PyQt5.QtCore import QRectF
from PyQt5.QtWidgets import QApplication, QWidget, QInputDialog, QLineEdit

from .helpDialog import showHelpDialog

class DendriteCanvasActions():
    COLOR_SENSITIVITY = 10.0 / 256.0

    def __init__(self, dendriteCanvas, model, uiState):
        self.canvas = dendriteCanvas
        self.model = model
        self.uiState = uiState

    def zoom(self, logAmount):
        self.canvas.imgView.zoom(logAmount)

    def pan(self, xDelta, yDelta):
        outsideRect = self.canvas.imgView.sceneRect()
        viewBox = self.canvas.imgView.getViewportRect()

        xDeltaPx = (int)(xDelta * viewBox.width() * 0.1)
        yDeltaPx = (int)(yDelta * viewBox.height() * 0.1)

        if xDeltaPx < outsideRect.left() - viewBox.left():
            xDeltaPx = outsideRect.left() - viewBox.left()
        elif xDeltaPx > outsideRect.right() - viewBox.right():
            xDeltaPx = outsideRect.right() - viewBox.right()

        if yDeltaPx < outsideRect.top() - viewBox.top():
            yDeltaPx = outsideRect.top() - viewBox.top()
        elif yDeltaPx > outsideRect.bottom() - viewBox.bottom():
            yDeltaPx = outsideRect.bottom() - viewBox.bottom()

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

    def deleteCurrentPoint(self):
        self.uiState.deletePoint(self.uiState.currentPoint())
        self.canvas.redraw()

    def showHotkeys(self):
        showHelpDialog()
