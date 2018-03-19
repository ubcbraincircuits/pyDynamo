from PyQt5.QtGui import QPen, QPainter, QBrush, QFont, QColor
from PyQt5.QtCore import Qt, QPointF, QRectF

import matplotlib.pyplot as plt
import numpy as np

# LINE_COLOR_COUNT = 7
# LINE_COLORS = plt.get_cmap('hsv')(np.arange(0.0, 1.0, 1.0/LINE_COLOR_COUNT))[:, :3]

# def colorForBranch(branchNumber):
    # return LINE_COLORS[(branchNumber + 1) % LINE_COLOR_COUNT] # +1 to start at yellow, not red.

"""
"""
class LandmarkPainter():
    # TODO - scale with zoom.
    NODE_CIRCLE_DIAMETER = 5
    NODE_CIRCLE_PEN = QPen(QBrush(Qt.black), 1, Qt.SolidLine)
    NODE_CIRCLE_BRUSH = QBrush(Qt.white)
    NODE_CIRCLE_SELECTED_BRUSH = QBrush(Qt.cyan)
    NODE_CIRCLE_MOVING_BRUSH = QBrush(Qt.red)

    ANNOTATION_PEN = QPen(QBrush(Qt.yellow), 1, Qt.SolidLine)
    ANNOTATION_FONT = QFont("Arial", 12, QFont.Bold)
    HEADER_PADDING = 20
    HEADER_MAX_WIDTH = 512

    def __init__(self, painter, currentZ, uiState, zoomMapFunc):
        self.p = painter
        self.zAt = currentZ
        self.uiState = uiState
        self.zoomMapFunc = zoomMapFunc
        self.branchAt = 0

    def drawLandmarks(self, landmarks, landmarkPointIdx):
        self.drawHeader(landmarkPointIdx)
        for i, landmark in enumerate(landmarks):
            self.drawLandmark(landmark, i == landmarkPointIdx)

    def drawLandmark(self, landmark, isCurrent):
        x, y, z = self.zoomedLocation(point.location)
        annotation = point.annotation
        self.drawCircle(x, y, isCurrent)

    def drawCircleThisZ(self, x, y, isCurent):
        brushColor = self.NODE_CIRCLE_BRUSH
        if isSelected:
            brushColor = self.NODE_CIRCLE_MOVING_BRUSH if self.uiState.isMoving else self.NODE_CIRCLE_SELECTED_BRUSH
        self.p.setPen(self.NODE_CIRCLE_PEN)
        self.p.setBrush(brushColor)
        self.p.drawEllipse(QPointF(x, y), self.NODE_CIRCLE_DIAMETER, self.NODE_CIRCLE_DIAMETER)

    def drawHeader(self, landmarkPointIdx):
        self.p.setFont(self.ANNOTATION_FONT)
        self.p.setPen(self.ANNOTATION_PEN)
        topLeft = QRectF(self.HEADER_PADDING, 0, self.HEADER_MAX_WIDTH, 2 * self.HEADER_PADDING)
        text = "Landmark, point %d" % (landmarkPointIdx)
        self.p.drawText(topLeft, Qt.AlignVCenter, text)

    def zoomedLocation(self, xyz):
        x, y, z = xyz
        zoomedXY = self.zoomMapFunc(x, y)
        return (zoomedXY.x(), zoomedXY.y(), z)
