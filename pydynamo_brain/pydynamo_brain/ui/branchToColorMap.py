from PyQt5.QtGui import QPen, QPainter, QBrush, QFont, QColor
from PyQt5.QtCore import Qt, QPointF, QRectF

import matplotlib.pyplot as plt
import numpy as np

LINE_COLOR_COUNT = 7
LINE_COLORS = plt.get_cmap('hsv')(np.arange(0.0, 1.0, 1.0/LINE_COLOR_COUNT))[:, :3]

class BranchToColorMap():
    def rgbForBranch(self, branchNumber):
        return LINE_COLORS[(branchNumber + 1) % LINE_COLOR_COUNT] # +1 to start at yellow, not red.

    def colorForBranch(self, branchNumber):
        rgb = self.rgbForBranch(branchNumber)
        return QColor.fromRgbF(rgb[0], rgb[1], rgb[2])
