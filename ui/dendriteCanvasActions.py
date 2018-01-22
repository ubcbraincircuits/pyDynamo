from PyQt5.QtCore import QRectF
from PyQt5.QtWidgets import QApplication, QWidget, QInputDialog, QLineEdit

class DendriteCanvasActions():
    def __init__(self, dendriteCanvas, model, uiOptions):
        self.canvas = dendriteCanvas
        self.model = model
        self.uiOptions = uiOptions

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

    def getAnnotation(self, window):
        currentBranch, currentPoint = self.model.currentBranch, self.uiOptions.currentPoint
        if currentPoint is None or currentBranch is None:
            # TODO - error alert?
            print ("No current point selected")
            return
        currentAnnotation = self.model.branches[currentBranch].annotations[currentPoint] or ''

        text, okPressed = QInputDialog.getText(window, "Annotate point", "Enter annotation:", QLineEdit.Normal, currentAnnotation)
        if okPressed:
            print ("New annotation: " + text)
            self.model.branches[currentBranch].annotations[currentPoint] = text
