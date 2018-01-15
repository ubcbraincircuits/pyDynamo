from .baseMatplotlibCanvas import BaseMatplotlibCanvas

import numpy as np

class DendriteVolumeCanvas(BaseMatplotlibCanvas):
    INVERT_SCROLL = False
    SCROLL_SENSITIVITY = 30.0

    def __init__(self, volume, *args, **kwargs):
        self.volume = volume
        self.zAxisAt = 0
        super(DendriteVolumeCanvas, self).__init__(*args, **kwargs)

    def compute_initial_figure(self):
        self.axes.imshow(self.volume[self.zAxisAt])

    def changeZAxis(self, delta):
        self.zAxisAt = self.zAxisAt + delta
        self.zAxisAt = max(min(self.zAxisAt, len(self.volume) - 1), 0)
        self.redraw()

    def redraw(self):
        self.axes.cla()
        self.axes.imshow(self.volume[self.zAxisAt])
        self.draw()

    def mousePressEvent(self, event):
        print ("Clicked: (%d %d)" % (event.globalX(), event.globalY()))
        super(DendriteVolumeCanvas, self).mousePressEvent(event)

    def wheelEvent(self,event):
        scrollDelta = -(int)(np.ceil(event.pixelDelta().y() / self.SCROLL_SENSITIVITY))
        if self.INVERT_SCROLL:
            scrollDelta *= -1
        self.changeZAxis(scrollDelta)
