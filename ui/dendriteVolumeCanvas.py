from .baseMatplotlibCanvas import BaseMatplotlibCanvas

import numpy as np

class DendriteVolumeCanvas(BaseMatplotlibCanvas):
    INVERT_SCROLL = False
    SCROLL_SENSITIVITY = 30.0
    COLOR_SENSITIVITY = 10.0 / 256.0

    def __init__(self, volume, *args, **kwargs):
        self.volume = volume
        self.zAxisAt = 0
        super(DendriteVolumeCanvas, self).__init__(*args, **kwargs)

    def compute_initial_figure(self):
        self.colorLimits = (0, 1)
        # self.drawImage()
        self.axes.imshow(self.volume[0], cmap='gray')

    def changeZAxis(self, delta):
        self.zAxisAt = self.snapToRange(self.zAxisAt + delta, 0, len(self.volume) - 1)
        self.redraw()

    def redraw(self):
        self.axes.cla()
        self.drawImage()
        self.draw()

    def drawImage(self):
        c1, c2 = self.colorLimits
        # hack - use clim if possible instead.
        imageData = np.array(self.volume[self.zAxisAt])
        imageData = imageData / np.amax(imageData)
        imageData = (imageData - c1) / (c2 - c1)
        imageData = self.snapToRange(imageData, 0.0, 1.0)
        self.axes.imshow(imageData, cmap='gray')

    def changeBrightness(self, lowerDelta, upperDelta):
        self.colorLimits = (
            self.snapToRange(self.colorLimits[0] + lowerDelta, 0, self.colorLimits[1] - 0.001),
            self.snapToRange(self.colorLimits[1] + upperDelta, self.colorLimits[0] + 0.001, 1),
        )
        self.redraw()

    def mousePressEvent(self, event):
        print ("Clicked: (%d %d)" % (event.globalX(), event.globalY()))
        super(DendriteVolumeCanvas, self).mousePressEvent(event)

    def wheelEvent(self,event):
        scrollDelta = -(int)(np.ceil(event.pixelDelta().y() / self.SCROLL_SENSITIVITY))
        if self.INVERT_SCROLL:
            scrollDelta *= -1
        self.changeZAxis(scrollDelta)

    # HACK - move to common
    def snapToRange(self, x, lo, hi):
        return np.maximum(lo, np.minimum(hi, x))

    def brightnessAction(self, lower, upper, reset=False):
        if reset:
            self.colorLimits = (0, 1)
            self.redraw()
        else:
            self.changeBrightness(lower * self.COLOR_SENSITIVITY, upper * self.COLOR_SENSITIVITY)
