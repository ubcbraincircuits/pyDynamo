from PyQt5.QtGui import QPen, QPainter, QBrush, QFont, QColor
from PyQt5.QtCore import Qt, QPointF, QRectF

import matplotlib.pyplot as plt
import numpy as np

import pydynamo_brain.util as util

LINE_COLOR_COUNT = 7
LINE_COLORS = plt.get_cmap('hsv')(np.arange(0.0, 1.0, 1.0/LINE_COLOR_COUNT))[:, :3]

def colorForBranch(branchNumber):
    return LINE_COLORS[(branchNumber + 1) % LINE_COLOR_COUNT] # +1 to start at yellow, not red.

"""
White dot = point on this plane
Green dot = current point
Solid line = line with end on this plne
Dashed line = line without end on this plane
Only draw ones with Z < 3 difference, UNLESS all are drawn
"""
class DendritePainter():
    NODE_CIRCLE_PEN = QPen(QBrush(Qt.black), 1, Qt.SolidLine)
    NODE_CIRCLE_BRUSH = QBrush(Qt.white)
    NODE_CIRCLE_SELECTED_BRUSH = QBrush(Qt.cyan)
    NODE_CIRCLE_MOVING_BRUSH = QBrush(Qt.red)
    NODE_CIRCLE_REPARENTING_BRUSH = QBrush(Qt.blue)
    NODE_CIRCLE_DEFAULT_RADIUS = 5
    MARKED_CIRCLE_BRUSH = QBrush(QColor(255, 108, 180))

    ANNOTATION_PEN = QPen(QBrush(Qt.yellow), 1, Qt.SolidLine)
    ANNOTATION_FONT = QFont("Arial", 12, QFont.Bold)
    ANNOTATION_OFFSET = 20
    ANNOTATION_HEIGHT = 40
    ANNOTATION_MAX_WIDTH = 512

    def __init__(self, painter, uiState, zoomMapFunc, zoomDistFunc):
        self.p = painter
        self.uiState = uiState
        self.zAt = self.uiState.zAxisAt
        self.zoomMapFunc = zoomMapFunc
        self.zoomDistFunc = zoomDistFunc
        self.branchAt = 0

    def drawTree(self, tree):
        if self.uiState.hideAll:
            return # Hidden, no paint for you.

        selectedPoint = self.uiState.currentPoint()
        selectedPointID = None if selectedPoint is None else selectedPoint.id

        for branch in tree.branches:
            self.drawBranchLines(branch)
            self.branchAt = self.branchAt + 1
        if tree.rootPoint is not None:
            self.drawPoint(tree.rootPoint, selectedPointID)
        for branch in tree.branches:
            self.drawBranchPoints(branch, selectedPointID)

    def drawBranchLines(self, branch):
        for i in range(len(branch.points)):
            previousPoint = branch.parentPoint if i == 0 else branch.points[i - 1]
            if previousPoint is None:
                continue # In theory should not get triggered, but added just in case.
            lastX, lastY, lastZ = self.zoomedLocation(previousPoint.location)
            thisX, thisY, thisZ = self.zoomedLocation(branch.points[i].location)
            linePen = self.getLinePen(lastZ, thisZ)
            if linePen is not None:
                self.p.setPen(linePen)
                self.p.drawLine(lastX, lastY, thisX, thisY)

    def drawBranchPoints(self, branch, selectedPointID):
        for i in range(len(branch.points)):
            self.drawPoint(branch.points[i], selectedPointID)

    def drawPoint(self, point, selectedPointID):
        x, y, z = self.zoomedLocation(point.location)
        if round(z) == self.zAt:
            # Hilighting has been removed, keep here for backwards compatibility
            marked = point.manuallyMarked or point.hilighted
            self.drawCircleThisZ(x, y,
                point.id == selectedPointID, marked,
                self.uiState.parent().dotSize, point.radius
            )
            self.maybeDrawText(x, y, point)

    def drawCircleThisZ(self, x, y, isSelected, isMarked, fakeRadius, realRadius):
        radius = fakeRadius
        resizeRadius = False
        if radius is None:
            radius = realRadius
            resizeRadius = (realRadius is not None)
        if radius is None:
            radius = self.NODE_CIRCLE_DEFAULT_RADIUS

        brushColor = self.NODE_CIRCLE_BRUSH
        if isSelected:
            brushColor = self.NODE_CIRCLE_SELECTED_BRUSH
            if self.uiState.isMoving:
                brushColor = self.NODE_CIRCLE_MOVING_BRUSH
            elif self.uiState.isReparenting:
                brushColor = self.NODE_CIRCLE_REPARENTING_BRUSH
        elif isMarked and self.uiState.showMarked:
            brushColor = self.MARKED_CIRCLE_BRUSH
        self.p.setPen(self.NODE_CIRCLE_PEN)
        self.p.setBrush(brushColor)
        if resizeRadius:
            radiusX, radiusY = self.zoomDistFunc(radius, radius)
        else:
            radiusX, radiusY = radius, radius
        self.p.drawEllipse(QPointF(x, y), radiusX, radiusY)

    def maybeDrawText(self, x, y, point):
        if not self.uiState.showAnnotations and not self.uiState.showIDs:
            return

        text = ""
        if self.uiState.showIDs:
            text = point.id
        if self.uiState.showAnnotations:
            text = point.annotation
        if text == "":
            return

        self.p.setFont(self.ANNOTATION_FONT)
        self.p.setPen(self.ANNOTATION_PEN)
        textRect = QRectF(
            x + self.ANNOTATION_OFFSET, y - self.ANNOTATION_HEIGHT / 2,
            self.ANNOTATION_MAX_WIDTH, self.ANNOTATION_HEIGHT
        )
        self.p.drawText(textRect, Qt.AlignVCenter, text)

    def getLinePen(self, z1, z2):
        same1, same2 = round(z1) == self.zAt, round(z2) == self.zAt
        near1, near2 = self.isNearZ(z1), self.isNearZ(z2)

        drawAll = (self.uiState.branchDisplayMode == 1)
        drawNear = not (self.uiState.branchDisplayMode == 2)
        if same1 or same2:
            color = colorForBranch(self.branchAt)
            color = QColor.fromRgbF(color[0], color[1], color[2])
            return QPen(QBrush(color), self.uiState.parent().lineWidth, Qt.SolidLine)
        elif drawNear and (near1 or near2 or drawAll):
            color = colorForBranch(self.branchAt)
            color = QColor.fromRgbF(color[0], color[1], color[2])
            return QPen(QBrush(color), self.uiState.parent().lineWidth, Qt.DotLine)
        else:
            return None

    def zoomedLocation(self, xyz):
        x, y, z = xyz
        zoomedXY = self.zoomMapFunc(x, y)
        return (zoomedXY.x(), zoomedXY.y(), z)

    # HACK - utilities
    def isNearZ(self, z):
        return abs(z - self.zAt) < 3
