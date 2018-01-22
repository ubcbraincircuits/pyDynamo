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

    CIRCLE_THIS_Z_PEN = QPen(QBrush(Qt.black), 1, Qt.SolidLine)
    CIRCLE_THIS_Z_BRUSH = QBrush(Qt.white)

    ANNOTATION_PEN = QPen(QBrush(Qt.yellow), 1, Qt.SolidLine)
    ANNOTATION_FONT = QFont("Arial", 12, QFont.Bold)
    NODE_CIRCLE_RADIUS = 5

    p = None

    def begin(self, painter, currentZ, options):
        assert self.p == None
        self.p = painter
        self.zAt = currentZ
        self.options = options

    def end(self):
        self.p = None
        self.zAt = None
        self.options = None

    def drawTree(self, tree):
        for branch in tree.branches:
            self.drawBranchLines(branch)
        for branch in tree.branches:
            self.drawBranchPoints(branch)

    def drawBranchLines(self, branch):
        lastX, lastY, lastZ = None, None, None
        for i in range(len(branch.points)):
            thisX, thisY, thisZ = branch.points[i]
            if lastZ is not None:

                linePen = self.getLinePen(lastZ, thisZ)
                if linePen is not None:
                    self.p.setPen(linePen)
                    self.p.drawLine(lastX, lastY, thisX, thisY)
            lastX, lastY, lastZ = thisX, thisY, thisZ

    def drawBranchPoints(self, branch):
        for i in range(len(branch.points)):
            x, y, z = branch.points[i]
            annotation = branch.annotations[i]
            if z == self.zAt:
                self.drawCircleThisZ(x, y)
                print ("%d -> %s" % (i, annotation))
                if annotation != "":
                    self.drawAnnotation(x, y, annotation)

    def drawCircleThisZ(self, x, y):
        self.p.setPen(self.CIRCLE_THIS_Z_PEN)
        self.p.setBrush(self.CIRCLE_THIS_Z_BRUSH)
        self.p.drawEllipse(QPointF(x, y), self.NODE_CIRCLE_RADIUS, self.NODE_CIRCLE_RADIUS)

    def drawAnnotation(self, x, y, text):
        if not self.options.showAnnotations:
            return
        self.p.setFont(self.ANNOTATION_FONT)
        self.p.setPen(self.ANNOTATION_PEN)
        # TODO - move constants somewhere.
        LEFT_OFFSET = 20
        HEIGHT = 40
        MAX_WIDTH = 512
        textRect = QRectF(x + LEFT_OFFSET, y - HEIGHT / 2, MAX_WIDTH, HEIGHT)
        self.p.drawText(textRect, Qt.AlignVCenter, text)

    def getLinePen(self, z1, z2):
        inZ1, inZ2 = z1 == self.zAt, z2 == self.zAt
        near1, near2 = self.isNearZ(z1), self.isNearZ(z2)
        if inZ1 or inZ2:
            return self.ON_Z_LINE_PEN
        elif near1 or near2 or self.options.drawAllBranches: # TODO - drawAll option
            return self.NEAR_Z_LINE_PEN
        else:
            return None



    # HACK - utilities
    def isNearZ(self, z):
        return abs(z - self.zAt) < 3
