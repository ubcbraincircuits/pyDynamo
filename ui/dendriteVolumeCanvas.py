from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter
from PyQt5.QtWidgets import QWidget, QGridLayout, QApplication, QLayout

import numpy as np

from .baseMatplotlibCanvas import BaseMatplotlibCanvas
from .np2qt import np2qt
from .QtImageViewer import QtImageViewer
from .dendritePainter import DendritePainter
from .dendriteOverlay import DendriteOverlay

from util import deltaSz, snapToRange

class DendriteVolumeCanvas(QWidget):
    INVERT_SCROLL = False
    SCROLL_SENSITIVITY = 100.0

    def __init__(self,
        windowIndex, fullActions, uiState, dynamoWindow,
        *args, **kwargs
    ):
        super(DendriteVolumeCanvas, self).__init__(*args, **kwargs)
        self.windowIndex = windowIndex
        self.fullActions = fullActions
        self.uiState = uiState
        self.dynamoWindow = dynamoWindow

        self.imgView = QtImageViewer(self,
            np2qt(uiState.currentImage(), normalize=True, channel=self.uiState.parent().colorChannel())
        )
        self.imgOverlay = DendriteOverlay(self)

        l = QGridLayout(self)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSizeConstraint(QLayout.SetFixedSize)
        l.addWidget(self.imgView, 0, 0)
        l.addWidget(self.imgOverlay, 0, 0)
        self.drawImage()

    def updateState(self, newUiState):
        self.uiState = newUiState
        self.redraw()

    def redraw(self):
        self.drawImage()

    def drawImage(self):
        c1, c2 = self.uiState.colorLimits
        # TODO: use inbuilt clim if possible instead.
        # imageData = np.array(self.volume[self.uiState.parent().zAxisAt])
        imageData = self.uiState.currentImage()
        imageData = imageData / np.amax(imageData)
        imageData = (imageData - c1) / (c2 - c1)
        imageData = snapToRange(imageData, 0.0, 1.0)
        self.imgView.setImage(
            np2qt(imageData, normalize=True, channel=self.uiState.parent().colorChannel()),
            maintainZoom=True)

    def mouseClickEvent(self, event, pos):
        super(DendriteVolumeCanvas, self).mousePressEvent(event)
        print ("DVC w/h = ", self.frameGeometry().width(), self.frameGeometry().height())
        location = (pos.x(), pos.y(), self.uiState.parent().zAxisAt)

        # Shortcut out landmark mode:
        if self.uiState.parent().inLandmarkMode():
            self.fullActions.setLandmark(self.windowIndex, location)
            self.dynamoWindow.redrawAllStacks()
            return

        modifiers = QApplication.keyboardModifiers()
        shiftPressed = modifiers & Qt.ShiftModifier
        rightClick = event.button() == Qt.RightButton

        pointClicked = self.uiState._tree.closestPointTo(location, zFilter=True)
        closestDist = None if pointClicked is None else deltaSz(location, pointClicked.location)
        if closestDist is None or closestDist >= DendritePainter.NODE_CIRCLE_DIAMETER:
            pointClicked = None

        # Handle Right-click first; either delete the point, or start a new branch.
        if rightClick:
            if pointClicked:
                self.fullActions.deletePoint(self.windowIndex, pointClicked)
            else:
                self.fullActions.addPointToNewBranchAndSelect(self.windowIndex, location)
        # Next, moving; either switch moving point, cancel move, or move selected point to new spot.
        elif self.uiState.isMoving:
            if pointClicked:
                if shiftPressed:
                    self.fullActions.beginMove(self.windowIndex, pointClicked)
                else:
                    self.fullActions.selectPoint(self.windowIndex, pointClicked)
            else:
                self.fullActions.endMove(self.windowIndex, location, moveDownstream=shiftPressed)
        # Next. shift; either start move, or add mid-branch point
        elif shiftPressed:
            if pointClicked:
                self.fullActions.beginMove(self.windowIndex, pointClicked)
            else:
                self.fullActions.addPointMidBranchAndSelect(self.windowIndex, location)
        # Otherwise - handle no modifier; either select point, or add to end of current branch.
        else:
            if pointClicked:
                self.fullActions.selectPoint(self.windowIndex, pointClicked)
            else:
                self.fullActions.addPointToCurrentBranchAndSelect(self.windowIndex, location)
        self.dynamoWindow.redrawAllStacks() # HACK - redraw only those that have changed.


    def wheelEvent(self,event):
        scrollDelta = -(int)(np.ceil(event.angleDelta().y() / self.SCROLL_SENSITIVITY))
        if self.INVERT_SCROLL:
            scrollDelta *= -1
        self.fullActions.changeZAxis(scrollDelta)
        self.dynamoWindow.redrawAllStacks()
        return True
