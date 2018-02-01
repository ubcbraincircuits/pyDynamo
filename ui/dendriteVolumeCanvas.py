from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter
from PyQt5.QtWidgets import QWidget, QGridLayout, QApplication

import numpy as np

from .baseMatplotlibCanvas import BaseMatplotlibCanvas
from .np2qt import np2qt
from .QtImageViewer import QtImageViewer
from .dendritePainter import DendritePainter
from .dendriteOverlay import DendriteOverlay

from util import snapToRange

class DendriteVolumeCanvas(QWidget):
    INVERT_SCROLL = False
    SCROLL_SENSITIVITY = 60.0

    def __init__(self, volume, model, uiState, dynamoWindow, *args, **kwargs):
        super(DendriteVolumeCanvas, self).__init__(*args, **kwargs)
        self.volume = volume
        self.model = model
        self.uiState = uiState
        self.dynamoWindow = dynamoWindow

        l = QGridLayout(self)
        self.imgView = QtImageViewer(self, np2qt(volume[0], normalize=True))
        self.imgOverlay = DendriteOverlay(self)
        l.addWidget(self.imgView, 0, 0)
        l.addWidget(self.imgOverlay, 0, 0)

    def redraw(self):
        self.drawImage()

    def drawImage(self):
        c1, c2 = self.uiState.colorLimits
        # TODO: use inbuilt clim if possible instead.
        imageData = np.array(self.volume[self.uiState.parent().zAxisAt])
        imageData = imageData / np.amax(imageData)
        imageData = (imageData - c1) / (c2 - c1)
        imageData = snapToRange(imageData, 0.0, 1.0)
        self.imgView.setImage(np2qt(imageData, normalize=True), maintainZoom=True)

    def mouseClickEvent(self, event, pos):
        super(DendriteVolumeCanvas, self).mousePressEvent(event)
        location = (pos.x(), pos.y(), self.uiState.parent().zAxisAt)
        modifiers = QApplication.keyboardModifiers()
        shiftPressed = modifiers & Qt.ShiftModifier

        pointClicked, closestDist = self.uiState.closestPointInZPlane(location)
        if closestDist is None or closestDist >= DendritePainter.NODE_CIRCLE_DIAMETER:
            pointClicked = None

        if event.button() == Qt.RightButton:
            if pointClicked:
                self.uiState.deletePoint(pointClicked)
            else:
                self.uiState.addPointToNewBranchAndSelect(location)
        else:
            if shiftPressed:
                self.uiState.addPointMidBranchAndSelect(location)
            elif pointClicked:
                self.uiState.selectPoint(pointClicked)
            else:
                self.uiState.addPointToCurrentBranchAndSelect(location)
        self.drawImage()

    def wheelEvent(self,event):
        scrollDelta = -(int)(np.ceil(event.pixelDelta().y() / self.SCROLL_SENSITIVITY))
        if self.INVERT_SCROLL:
            scrollDelta *= -1
        self.dynamoWindow.changeZAxis(scrollDelta)
        return True
