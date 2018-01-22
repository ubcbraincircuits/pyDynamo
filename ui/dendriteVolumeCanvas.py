
from PyQt5.QtWidgets import QWidget, QHBoxLayout
import numpy as np

from .baseMatplotlibCanvas import BaseMatplotlibCanvas
from .np2qt import np2qt
from .QtImageViewer import QtImageViewer
from .dendritePainter import DendritePainter

# class DendriteVolumeCanvas(BaseMatplotlibCanvas):
class DendriteVolumeCanvas(QWidget):
    INVERT_SCROLL = False
    SCROLL_SENSITIVITY = 30.0
    COLOR_SENSITIVITY = 10.0 / 256.0

    def __init__(self, volume, model, uiOptions, HACKSCATTER, *args, **kwargs):
        super(DendriteVolumeCanvas, self).__init__(*args, **kwargs)
        self.volume = volume
        self.zAxisAt = 0
        self.colorLimits = (0, 1)
        self.model = model
        self.uiOptions = uiOptions

        self.HACKSCATTER = HACKSCATTER

        l = QHBoxLayout(self)
        self.imgView = QtImageViewer(self)
        self.imgView.setImage(np2qt(volume[0], normalize=True))
        l.addWidget(self.imgView)

    def changeZAxis(self, delta):
        self.zAxisAt = self.snapToRange(self.zAxisAt + delta, 0, len(self.volume) - 1)
        self.drawImage()

    def redraw(self):
        self.drawImage()

    def drawImage(self):
        c1, c2 = self.colorLimits
        # hack - use clim if possible instead.
        imageData = np.array(self.volume[self.zAxisAt])
        imageData = imageData / np.amax(imageData)
        imageData = (imageData - c1) / (c2 - c1)
        imageData = self.snapToRange(imageData, 0.0, 1.0)
        self.imgView.setImage(np2qt(imageData, normalize=True), maintainZoom=True)

    def changeBrightness(self, lowerDelta, upperDelta):
        self.colorLimits = (
            self.snapToRange(self.colorLimits[0] + lowerDelta, 0, self.colorLimits[1] - 0.001),
            self.snapToRange(self.colorLimits[1] + upperDelta, self.colorLimits[0] + 0.001, 1),
        )
        self.drawImage()

    def mouseClickEvent(self, event, pos):
        super(DendriteVolumeCanvas, self).mousePressEvent(event)
        self.model.addPoint((pos.x(), pos.y(), self.zAxisAt))
        self.HACKSCATTER.needToUpdate()
        self.drawImage()

    def wheelEvent(self,event):
        scrollDelta = -(int)(np.ceil(event.pixelDelta().y() / self.SCROLL_SENSITIVITY))
        if self.INVERT_SCROLL:
            scrollDelta *= -1
        self.changeZAxis(scrollDelta)
        return True

    # HACK - move to common
    def snapToRange(self, x, lo, hi):
        return np.maximum(lo, np.minimum(hi, x))

    def brightnessAction(self, lower, upper, reset=False):
        if reset:
            self.colorLimits = (0, 1)
            self.drawImage()
        else:
            self.changeBrightness(lower * self.COLOR_SENSITIVITY, upper * self.COLOR_SENSITIVITY)
