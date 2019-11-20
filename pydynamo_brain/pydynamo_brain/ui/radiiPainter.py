from PyQt5.QtGui import QPen, QPainter, QBrush, QFont, QColor
from PyQt5.QtCore import Qt, QPointF, QRectF

import matplotlib.pyplot as plt
import math
import numpy as np

import pydynamo_brain.util as util

"""
Red Radii = Points with None as radius vaule
Orange Radii = Radius with a real value
Cyan dot and Cyan Radi = selected point and radius
Solid line = line with end on this plne
Dashed line = line without end on this plane
Only draw ones with Z < 3 difference, UNLESS all are drawn
"""
class RadiiPainter():
    NODE_CIRCLE_PEN = QPen(QBrush(Qt.black), 1, Qt.SolidLine)
    NODE_CIRCLE_BRUSH = QBrush(QColor.fromRgbF(1.0, 1.0, 1.0, 0.5))
    NODE_CIRCLE_SELECTED_BRUSH = QBrush(QColor.fromRgbF(0, 1.0, 1.0, 0.5))
    NODE_CIRCLE_MOVING_BRUSH = QBrush(QColor.fromRgbF(1.0, 0, 0, 0.5))
    NODE_CIRCLE_REPARENTING_BRUSH = QBrush(QColor.fromRgbF(0, 0, 1.0, 0.5))
    NODE_CIRCLE_DEFAULT_RADIUS = 5
    MARKED_CIRCLE_BRUSH = QBrush(QColor(255, 108, 180))

    ANNOTATION_PEN = QPen(QBrush(Qt.yellow), 1, Qt.SolidLine)
    ANNOTATION_FONT = QFont("Arial", 12, QFont.Bold)
    ANNOTATION_OFFSET = 20
    ANNOTATION_HEIGHT = 40
    ANNOTATION_MAX_WIDTH = 512

    #Colors for Radius Calipers
    RAIDUS_COLOR_NONE = (219, 164, 11)
    RAIDUS_COLOR_REAL = (255,0,255)
    RAIDUS_COLOR_SELECTED = (11, 219, 209)

    def __init__(self, painter, uiState, zoomMapFunc, zoomDistFunc):
        self.p = painter
        self.uiState = uiState
        self.zAt = self.uiState.zAxisAt
        self.zoomMapFunc = zoomMapFunc
        self.zoomDistFunc = zoomDistFunc

    def drawTree(self, tree):
        if self.uiState.hideAll:
            return # Hidden, no paint for you.

        selectedPoint = self.uiState.currentPoint()
        selectedPointID = None if selectedPoint is None else selectedPoint.id

        for branch in tree.branches:
            self.drawBranchLines(branch)
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
            linePen = self.getLinePen(branch, lastZ, thisZ)
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
                self.uiState.parent().dotSize, point.radius, point
            )
            self.maybeDrawText(x, y, point)

    def returnRadiusCoord(self, point, radius):
        #point radius will be drawn from
        delta = 1

        """        #previous point
        posX, posY, negX, negY = x2, y2, x2, y2,"""
        if  point.isRoot():
            #print(point.isRoot)
            nextPoint  = point.nextPointInBranch(delta)
            #print(nextPoint)
            p2Loc = point.location
            #print(p2Loc)
            x2, y2, z2 = self.zoomedLocation(p2Loc)

            p1Loc = nextPoint.location
            x1, y1, z1 = self.zoomedLocation(p1Loc)


        else:
            p2Loc = point.location
            x2, y2, z2 = self.zoomedLocation(p2Loc)
            point1 =  point.pathFromRoot()[-2:][0]
            p1Loc = point1.location
            x1, y1, z1 = self.zoomedLocation(p1Loc)

        #length between two points
        L = math.sqrt(math.pow((x2-x1),2)+math.pow((y2-y1),2))
        if L == 0:
            L = 1
        #all solutions for the plotting radius
        #assuming a right triangle
        negX = x2 -((radius*(y1-y2)/L))
        posX = x2 +((radius*(y1-y2)/L))
        posY = y2 +((radius*(x1-x2)/L))
        negY = y2 -((radius*(x1-x2)/L))

        return negX, posY, posX, negY

    def drawCircleThisZ(self, x, y, isSelected, isMarked, fakeRadius, realRadius, point):
        if realRadius is not None:
            radius2Draw = realRadius
            rgbRadius = self.RAIDUS_COLOR_NONE
        else:
            radius2Draw = 10
            rgbRadius = self.RAIDUS_COLOR_REAL
        radius = fakeRadius
        resizeRadius = False
        if radius is None:
            radius = realRadius
            resizeRadius = (realRadius is not None)
        if radius is None:
            radius = self.NODE_CIRCLE_DEFAULT_RADIUS

        #scale radius for image view
        radius2Draw, junk = self.zoomDistFunc(radius2Draw, radius2Draw)
        #calculate the line to represent neurite radius
        x1, y1, x2, y2 = self.returnRadiusCoord(point, radius2Draw)

        brushColor = self.NODE_CIRCLE_BRUSH
        if isSelected:
            rgbRadius = self.RAIDUS_COLOR_SELECTED
            brushColor = self.NODE_CIRCLE_SELECTED_BRUSH
            if self.uiState.isMoving():
                brushColor = self.NODE_CIRCLE_MOVING_BRUSH
            elif self.uiState.isReparenting():
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
        #self.p.end()
        #draw lines to represent the size of the radius
        radiColor = QColor(*rgbRadius)

        #Pen for drawing radi
        self.p.setPen(QPen(QBrush(radiColor), self.uiState.parent().lineWidth, Qt.DotLine))
        self.p.drawLine(x1, y1, x2, y2)


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

    def getLinePen(self, branch, z1, z2):
        color = QColor(255, 255, 0)

        same1, same2 = round(z1) == self.zAt, round(z2) == self.zAt
        near1, near2 = self.isNearZ(z1), self.isNearZ(z2)

        drawAll = (self.uiState.branchDisplayMode == 1)
        drawNear = not (self.uiState.branchDisplayMode == 2)
        if same1 or same2:
            return QPen(QBrush(color), self.uiState.parent().lineWidth, Qt.SolidLine)
        elif drawNear and (near1 or near2 or drawAll):
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
