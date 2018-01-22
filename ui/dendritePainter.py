from PyQt5.QtGui import QPen, QPainter, QBrush, QFont
from PyQt5.QtCore import Qt, QPointF, QRectF

"""
White dot = point on this plane
Green dot = current point
Solid line = line with end on this plne
Dashed line = line without end on this plane
Only draw ones with Z < 3 difference, UNLESS all are drawn
"""
class DendritePainter():
    ON_Z_LINE_PEN = QPen(QBrush(Qt.yellow), 3, Qt.SolidLine)
    NEAR_Z_LINE_PEN = QPen(QBrush(Qt.yellow), 3, Qt.DashLine)

    NODE_CIRCLE_RADIUS = 5
    NODE_CIRCLE_PEN = QPen(QBrush(Qt.black), 1, Qt.SolidLine)
    NODE_CIRCLE_BRUSH = QBrush(Qt.white)

    ANNOTATION_PEN = QPen(QBrush(Qt.yellow), 1, Qt.SolidLine)
    ANNOTATION_FONT = QFont("Arial", 12, QFont.Bold)
    ANNOTATION_OFFSET = 20
    ANNOTATION_HEIGHT = 40
    ANNOTATION_MAX_WIDTH = 512

    def __init__(self, painter, currentZ, uiState):
        self.p = painter
        self.zAt = currentZ
        self.uiState = uiState

    def drawTree(self, tree):
        for branch in tree.branches:
            self.drawBranchLines(branch)
        for branch in tree.branches:
            self.drawBranchPoints(branch)

    def drawBranchLines(self, branch):
        for i in range(1, len(branch.points)):
            lastX, lastY, lastZ = branch.points[i-1].location
            thisX, thisY, thisZ = branch.points[ i ].location
            linePen = self.getLinePen(lastZ, thisZ)
            if linePen is not None:
                self.p.setPen(linePen)
                self.p.drawLine(lastX, lastY, thisX, thisY)

    def drawBranchPoints(self, branch):
        for i in range(len(branch.points)):
            x, y, z = branch.points[i].location
            annotation = branch.points[i].annotation
            if z == self.zAt:
                self.drawCircleThisZ(x, y)
                if annotation != "":
                    self.drawAnnotation(x, y, annotation)

    def drawCircleThisZ(self, x, y):
        self.p.setPen(self.NODE_CIRCLE_PEN)
        self.p.setBrush(self.NODE_CIRCLE_BRUSH)
        self.p.drawEllipse(QPointF(x, y), self.NODE_CIRCLE_RADIUS, self.NODE_CIRCLE_RADIUS)

    def drawAnnotation(self, x, y, text):
        if not self.uiState.showAnnotations:
            return
        self.p.setFont(self.ANNOTATION_FONT)
        self.p.setPen(self.ANNOTATION_PEN)
        textRect = QRectF(
            x + self.ANNOTATION_OFFSET, y - self.ANNOTATION_HEIGHT / 2,
            self.ANNOTATION_MAX_WIDTH, self.ANNOTATION_HEIGHT
        )
        self.p.drawText(textRect, Qt.AlignVCenter, text)

    def getLinePen(self, z1, z2):
        inZ1, inZ2 = z1 == self.zAt, z2 == self.zAt
        near1, near2 = self.isNearZ(z1), self.isNearZ(z2)
        if inZ1 or inZ2:
            return self.ON_Z_LINE_PEN
        elif near1 or near2 or self.uiState.drawAllBranches:
            return self.NEAR_Z_LINE_PEN
        else:
            return None



    # HACK - utilities
    def isNearZ(self, z):
        return abs(z - self.zAt) < 3
