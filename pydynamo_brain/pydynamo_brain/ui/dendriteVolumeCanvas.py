from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter
from PyQt5.QtWidgets import QWidget, QGridLayout, QApplication, QLayout

import math
import numpy as np

from .baseMatplotlibCanvas import BaseMatplotlibCanvas
from .np2qt import np2qt
from .QtImageViewer import QtImageViewer
from .dendritePainter import DendritePainter
from .dendriteOverlay import DendriteOverlay

from pydynamo_brain.model import Point
from pydynamo_brain.util import ImageCache, deltaSz, snapToRange, zStackForUiState


_IMGCACHE = ImageCache()

class DendriteVolumeCanvas(QWidget):
    INVERT_SCROLL = False
    SCROLL_SENSITIVITY = 100.0

    def __init__(self,
        windowIndex, fullActions, uiState, dynamoWindow, stackWindow,
        *args, **kwargs
    ):
        super(DendriteVolumeCanvas, self).__init__(*args, **kwargs)
        self.windowIndex = windowIndex
        self.fullActions = fullActions
        self.uiState = uiState
        self.dynamoWindow = dynamoWindow
        self.stackWindow = stackWindow
        self.history = dynamoWindow.history

        self.imgView = QtImageViewer(self,
            np2qt(self.currentImg(), normalize=True, channel=self.uiState.parent().colorChannel())
        )
        self.imgOverlay = DendriteOverlay(self, windowIndex)

        l = QGridLayout(self)
        l.setContentsMargins(0, 0, 0, 0)
        # l.setSizeConstraint(QLayout.SetFixedSize)
        l.addWidget(self.imgView, 0, 0)
        l.addWidget(self.imgOverlay, 0, 0)

        self.drawImage()

    def currentImg(self):
        return _IMGCACHE.imageForUIState(self.uiState)

    def updateState(self, newUiState):
        self.uiState = newUiState
        self.redraw()

    def updateWindowIndex(self, windowIndex):
        self.windowIndex = windowIndex
        self.imgOverlay.updateWindowIndex(windowIndex)

    def redraw(self):
        self.drawImage()

    def drawImage(self):
        c1, c2 = self.uiState.colorLimits
        imageData = self.currentImg()
        imageData = imageData / np.amax(imageData)
        imageData = (imageData - c1) / (c2 - c1)
        imageData = snapToRange(imageData, 0.0, 1.0)
        self.imgView.setImage(
            np2qt(imageData, normalize=True, channel=self.uiState.parent().colorChannel()),
            maintainZoom=True)

    def mouseClickEvent(self, event, pos):
        try:
            super(DendriteVolumeCanvas, self).mousePressEvent(event)
            zAt = zStackForUiState(self.uiState) * 1.0
            location = (pos.x(), pos.y(), zAt)

            # Shortcut out if the stack's tree is hidden:
            if self.uiState.hideAll:
                return

            modifiers = int(QApplication.keyboardModifiers())
            shiftPressed = (modifiers & Qt.ShiftModifier) > 0
            ctrlPressed = (modifiers & Qt.ControlModifier) > 0
            rightClick = event.button() == Qt.RightButton
            middleClick = event.button() == Qt.MidButton

            fullState = self.uiState.parent()

            # Shortcut out in puncta mode:
            if fullState.inPunctaMode():
                if self.handlePunctaClick(location, shiftPressed, ctrlPressed, rightClick, middleClick):
                    self.dynamoWindow.redrawAllStacks(self.stackWindow)
                return

            pointClicked = self.pointOnPixel(location)
            if pointClicked is not None:
                pointClicked.manuallyMarked = False

            # Handle manual registration first: select or deselect the point
            if fullState.inManualRegistrationMode():
                if pointClicked:
                    if shiftPressed:
                        # select all points with this ID in all stacks:
                        self.fullActions.selectPoint(
                            self.windowIndex, pointClicked, avoidPush=True, deselectHidden=True
                        )
                    else:
                        # select just this point in this stack:
                        self.uiState.selectOrDeselectPointID(pointClicked.id)

            # Next, reparent; either reparent, or cancel reparenting.
            elif self.uiState.isReparenting():
                if pointClicked:
                    self.fullActions.reparent(self.windowIndex, pointClicked)
                else:
                    # Nothing clicked, cancel reparent action
                    self.stackWindow.actionHandler.stopReplaceParent()

            # Next, moving; either switch moving point, cancel move, or move selected point to new spot.
            elif self.uiState.isMoving():
                if pointClicked:
                    if shiftPressed:
                        self.fullActions.beginMove(self.windowIndex, pointClicked)
                    else:
                       self.fullActions.selectPoint(self.windowIndex, pointClicked)

                else:
                    # NOTE: laterStacks is ctrl here, and shift for deletion.
                    # Not ideal, but downstream was already bound to shift here.
                    self.fullActions.endMove(self.windowIndex, location,
                        downstream=shiftPressed, laterStacks=ctrlPressed)

            # Radii Mode Click Events
            elif fullState.inRadiiMode():
                if pointClicked:
                    if pointClicked != self.uiState.currentPoint():
                        self.fullActions.selectPoint(self.windowIndex, pointClicked)
                else:
                    self.fullActions.radiiActions.editRadiiOnClick(location, self.uiState)

            # Next, Right-click/ctrl first; either delete the point, or start a new branch.
            elif rightClick or ctrlPressed:
                if pointClicked:
                    self.fullActions.deletePoint(self.windowIndex, pointClicked, laterStacks=shiftPressed)
                else:
                    if ctrlPressed and shiftPressed and not rightClick:
                        self.fullActions.addPointMidBranchAndSelect(self.windowIndex, location, backwards=True)
                    else:
                        self.fullActions.addPointToNewBranchAndSelect(self.windowIndex, location)

            # Next. Middle-click / shift; either start move, or add mid-branch point
            elif middleClick or shiftPressed:
                if pointClicked:
                    self.fullActions.beginMove(self.windowIndex, pointClicked)
                else:
                    assert not (ctrlPressed and not rightClick) # Ctrl-shift-left handled above
                    self.fullActions.addPointMidBranchAndSelect(self.windowIndex, location)
            # Otherwise - handle no modifier; either select point, or add to end of current branch.
            else:
                if pointClicked:
                    self.fullActions.selectPoint(self.windowIndex, pointClicked)
                else:
                    self.fullActions.addPointToCurrentBranchAndSelect(self.windowIndex, location)
            self.dynamoWindow.redrawAllStacks(self.stackWindow)
        except Exception as e:
            print ("Whoops - error on click: " + str(e))
            raise

    # Click actions handled specifically for when drawing puncta
    def handlePunctaClick(self, location, shiftPressed, ctrlPressed, rightClick, middleClick):
        pointClicked = self.punctaOnPixel(location)

        punctaActions = self.fullActions.punctaActions
        if rightClick:
            punctaActions.movePointBoundary(self.windowIndex, location)
        elif shiftPressed and not ctrlPressed:
            punctaActions.movePointCenter(self.windowIndex, location)
        elif pointClicked:
            if ctrlPressed:
                punctaActions.removePoint(
                    self.windowIndex, pointClicked, laterStacks=shiftPressed
                )
            else:
                punctaActions.selectPoint(self.windowIndex, pointClicked)
        else:
            punctaActions.createPuncta(self.windowIndex, location)
        return True

    def wheelEvent(self, event):
        try:
            scrollDelta = -(int)(np.ceil(event.angleDelta().y() / self.SCROLL_SENSITIVITY))
            if self.INVERT_SCROLL:
                scrollDelta *= -1
            self.fullActions.changeAllZAxis(scrollDelta, self.stackWindow)
            self.dynamoWindow.redrawAllStacks(self.stackWindow)
        except Exception as e:
            print ("Whoops - error on scroll: " + str(e))

    def pointOnPixel(self, location, zFilter=True):
        dotSize = self.uiState.parent().dotSize

        # TODO - share with below
        closestDist, closestPoint = None, None
        allPoints = self.uiState._tree.flattenPoints()
        for point in allPoints:
            if zFilter and round(point.location[2]) != round(location[2]):
                continue

            radius = dotSize
            resizeRadius = False
            if radius is None:
                radius = point.radius
                resizeRadius = (point.radius is not None)
            if radius is None:
                radius = DendritePainter.NODE_CIRCLE_DEFAULT_RADIUS
            if resizeRadius:
                radius, _ = self.imgView.fromSceneDist(radius, radius)

            # TODO - verify this always needs to happen, but not below?
            zLoc = self.zoomedLocation(location)
            zPLoc = self.zoomedLocation(point.location)
            dist = deltaSz(zLoc, zPLoc)
            if dist > radius:
                continue
            if closestDist is None or dist < closestDist:
                closestDist, closestPoint = dist, point

        return closestPoint

    def punctaOnPixel(self, location, zFilter=True):
        # TODO - share with above
        closestDist, closestPoint = None, None
        if self.windowIndex < len(self.uiState._parent.puncta):
            allPoints = self.uiState._parent.puncta[self.windowIndex]
            for point in allPoints:
                if zFilter and round(point.location[2]) != round(location[2]):
                    continue
                dist = deltaSz(location, point.location)
                if dist > point.radius:
                    continue
                if closestDist is None or dist < closestDist:
                    closestDist, closestPoint = dist, point
        return closestPoint

    # TODO - share with dendrite painter.
    def zoomedLocation(self, xyz):
        x, y, z = xyz
        zoomedXY = self.imgView.mapFromScene(x, y)
        return (zoomedXY.x(), zoomedXY.y(), z)
