from PyQt5.QtGui import QPen, QPainter, QBrush, QFont, QColor
from PyQt5.QtCore import Qt, QPointF, QRectF

import matplotlib.pyplot as plt
import numpy as np

"""
"""
class PunctaPainter():
    NODE_CIRCLE_PEN = QPen(QBrush(Qt.black), 1, Qt.SolidLine)
    NODE_CIRCLE_BRUSH = QBrush(QColor.fromRgbF(1.0, 1.0, 1.0, 0.6))
    NODE_CIRCLE_SELECTED_BRUSH = QBrush(QColor.fromRgbF(0.0, 1.0, 1.0, 0.6))
    NODE_CIRCLE_SELECTED_WRONGZ_PEN = QPen(QBrush(Qt.black), 1, Qt.DashLine)
    NODE_CIRCLE_WRONGZ_PEN = QPen(QBrush(QColor.fromRgbF(0.7, 0.7, 0.0, 0.9)), 2, Qt.DashLine)
    NODE_CIRCLE_WRONGZ_BRUSH = QBrush(QColor.fromRgbF(1.0, 1.0, 0.0, 0.5))

    ANNOTATION_PEN = QPen(QBrush(Qt.yellow), 1, Qt.SolidLine)
    ANNOTATION_FONT = QFont("Arial", 12, QFont.Bold)
    ANNOTATION_OFFSET = 10
    ANNOTATION_HEIGHT = 40
    ANNOTATION_MAX_WIDTH = 512

    def __init__(self, painter, windowIndex, uiState,
        zoomMapFunc, zoomDistFunc
    ):
        self.p = painter
        self.windowIndex = windowIndex
        self.uiState = uiState
        self.zAt = self.uiState.zAxisAt
        self.zoomMapFunc = zoomMapFunc
        self.zoomDistFunc = zoomDistFunc

    def updateWindowIndex(self, windowIndex):
        self.windowIndex = windowIndex

    def drawPuncta(self, punctaMap):
        selectedPuncta = self.uiState.currentPuncta()
        selectedID = None if selectedPuncta is None else selectedPuncta.id
        if self.windowIndex < len(self.uiState._parent.puncta):
            for point in self.uiState._parent.puncta[self.windowIndex]:
                self.drawPunctum(point, selectedID)

    def drawPunctum(self, point, selectedID):
        if point is None:
            return
        x, y, z = self.zoomedLocation(point.location)
        isCurrent = (point.id == selectedID)
        radiusPx = point.radius

        sameZ = round(z) == self.zAt
        nearZ = self.isNearZ(z)
        drawAll = (self.uiState.branchDisplayMode == 1)
        drawNear = not (self.uiState.branchDisplayMode == 2)

        # 0 = nearby, 1 = all, 2 = only on this Z plane
        draw = (sameZ or drawAll or (drawNear and nearZ))
        if draw:
            self.drawCircle(x, y, sameZ, radiusPx, isCurrent)
            self.maybeDrawText(x, y, point)

    def drawCircle(self, x, y, sameZ, radiusPx, isCurrent):
        assert radiusPx is not None
        radiusX, radiusY = self.zoomDistFunc(radiusPx, radiusPx)
        pen = self.NODE_CIRCLE_PEN
        brush = self.NODE_CIRCLE_BRUSH
        if isCurrent:
            brush = self.NODE_CIRCLE_SELECTED_BRUSH
            if not sameZ:
                pen = self.NODE_CIRCLE_SELECTED_WRONGZ_PEN
        elif not sameZ:
            pen = self.NODE_CIRCLE_WRONGZ_PEN
            brush = self.NODE_CIRCLE_WRONGZ_BRUSH
        self.p.setPen(pen)
        self.p.setBrush(brush)
        self.p.drawEllipse(QPointF(x, y), radiusX, radiusY)

    def zoomedLocation(self, xyz):
        x, y, z = xyz
        zoomedXY = self.zoomMapFunc(x, y)
        return (zoomedXY.x(), zoomedXY.y(), z)

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
        radiusX, _ = self.zoomDistFunc(point.radius, 0)

        textRect = QRectF(
            x + radiusX + self.ANNOTATION_OFFSET, y - self.ANNOTATION_HEIGHT / 2,
            self.ANNOTATION_MAX_WIDTH, self.ANNOTATION_HEIGHT
        )
        self.p.drawText(textRect, Qt.AlignVCenter, text)

    # HACK - utilities
    def isNearZ(self, z):
        return abs(z - self.zAt) < 3
