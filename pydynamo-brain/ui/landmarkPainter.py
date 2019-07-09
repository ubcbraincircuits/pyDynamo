from PyQt5.QtGui import QPen, QPainter, QBrush, QFont, QColor
from PyQt5.QtCore import Qt, QPointF, QRectF

import matplotlib.pyplot as plt
import numpy as np

"""
"""
class LandmarkPainter():
    NODE_CIRCLE_DIAMETER = 5

    NODE_CIRCLE_PEN = QPen(QBrush(Qt.darkRed), 2, Qt.SolidLine)
    NODE_CIRCLE_CURRENT_PEN = QPen(QBrush(Qt.darkCyan), 2, Qt.SolidLine)

    NODE_CIRCLE_BRUSH = QBrush(Qt.red)
    NODE_CIRCLE_CURRENT_BRUSH = QBrush(Qt.cyan)
    NODE_CIRCLE_WRONGZ_BRUSH = Qt.NoBrush

    ANNOTATION_PEN = QPen(QBrush(Qt.yellow), 1, Qt.SolidLine)
    ANNOTATION_FONT = QFont("Arial", 12, QFont.Bold)
    HEADER_PADDING = 20
    HEADER_MAX_WIDTH = 512

    def __init__(self, painter, uiState, zoomMapFunc):
        self.p = painter
        self.zAt = util.zStackForUiState(uiState)
        self.uiState = uiState
        self.zoomMapFunc = zoomMapFunc
        self.branchAt = 0

    def drawLandmarks(self, landmarks, landmarkPointIdx):
        self.drawHeader(landmarkPointIdx)
        for i, landmark in enumerate(landmarks):
            self.drawLandmark(landmark, i == landmarkPointIdx)

    def drawLandmark(self, landmark, isCurrent):
        if landmark is None:
            return
        x, y, z = self.zoomedLocation(landmark)
        self.drawCircle(x, y, z == self.zAt, isCurrent)

    def drawCircle(self, x, y, sameZ, isCurrent):
        brushColor, penColor = None, None
        pen = self.NODE_CIRCLE_CURRENT_PEN if isCurrent else self.NODE_CIRCLE_PEN
        if sameZ:
            brush = self.NODE_CIRCLE_CURRENT_BRUSH if isCurrent else self.NODE_CIRCLE_BRUSH
        else:
            brush = self.NODE_CIRCLE_WRONGZ_BRUSH

        self.p.setPen(pen)
        self.p.setBrush(brush)
        self.p.drawEllipse(QPointF(x, y), self.NODE_CIRCLE_DIAMETER, self.NODE_CIRCLE_DIAMETER)

    def drawHeader(self, landmarkPointIdx):
        self.p.setFont(self.ANNOTATION_FONT)
        self.p.setPen(self.ANNOTATION_PEN)
        topLeft = QRectF(self.HEADER_PADDING, 0, self.HEADER_MAX_WIDTH, 2 * self.HEADER_PADDING)
        text = "Landmark mode: Point %d" % (landmarkPointIdx + 1)
        self.p.drawText(topLeft, Qt.AlignVCenter, text)

    def zoomedLocation(self, xyz):
        x, y, z = xyz
        zoomedXY = self.zoomMapFunc(x, y)
        return (zoomedXY.x(), zoomedXY.y(), z)
