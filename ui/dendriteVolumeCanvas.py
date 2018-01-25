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
    SCROLL_SENSITIVITY = 30.0
    COLOR_SENSITIVITY = 10.0 / 256.0

    def __init__(self, volume, model, uiState, HACKSCATTER, *args, **kwargs):
        super(DendriteVolumeCanvas, self).__init__(*args, **kwargs)
        self.volume = volume
        self.zAxisAt = 0
        self.colorLimits = (0, 1)
        self.model = model
        self.uiState = uiState

        self.HACKSCATTER = HACKSCATTER

        l = QGridLayout(self)
        self.imgView = QtImageViewer(self, np2qt(volume[0], normalize=True))
        self.imgOverlay = DendriteOverlay(self)
        l.addWidget(self.imgView, 0, 0)
        l.addWidget(self.imgOverlay, 0, 0)

    def changeZAxis(self, delta):
        self.zAxisAt = snapToRange(self.zAxisAt + delta, 0, len(self.volume) - 1)
        self.drawImage()

    def redraw(self):
        self.drawImage()

    def drawImage(self):
        c1, c2 = self.colorLimits
        # hack - use clim if possible instead.
        imageData = np.array(self.volume[self.zAxisAt])
        imageData = imageData / np.amax(imageData)
        imageData = (imageData - c1) / (c2 - c1)
        imageData = snapToRange(imageData, 0.0, 1.0)
        self.imgView.setImage(np2qt(imageData, normalize=True), maintainZoom=True)

    # TODO: move to actions
    def changeBrightness(self, lowerDelta, upperDelta):
        self.colorLimits = (
            snapToRange(self.colorLimits[0] + lowerDelta, 0, self.colorLimits[1] - 0.001),
            snapToRange(self.colorLimits[1] + upperDelta, self.colorLimits[0] + 0.001, 1),
        )
        self.drawImage()

    def mouseClickEvent(self, event, pos):
        super(DendriteVolumeCanvas, self).mousePressEvent(event)
        location = (pos.x(), pos.y(), self.zAxisAt)

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
        self.HACKSCATTER.needToUpdate()
        self.drawImage()

    def wheelEvent(self,event):
        scrollDelta = -(int)(np.ceil(event.pixelDelta().y() / self.SCROLL_SENSITIVITY))
        if self.INVERT_SCROLL:
            scrollDelta *= -1
        self.changeZAxis(scrollDelta)
        return True

    # TODO - move colorLimits to uiState, action to dendriteCanvasActions
    def brightnessAction(self, lower, upper, reset=False):
        if reset:
            self.colorLimits = (0, 1)
            self.drawImage()
        else:
            self.changeBrightness(lower * self.COLOR_SENSITIVITY, upper * self.COLOR_SENSITIVITY)
