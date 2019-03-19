from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.Qt import Qt

import numpy as np
import pyqtgraph.opengl as gl

import util

_IMG_CACHE = util.ImageCache()

# Renders the entire volume as 3D voxels using openGL.
class Volume3DWindow(QtWidgets.QMainWindow):
    def __init__(self, parent, uiState, showGrid=False):
        QtWidgets.QMainWindow.__init__(self, parent)

        self.uiState = uiState

        # Find max height/width size, and take up as much as possible:
        size = QtWidgets.QDesktopWidget().availableGeometry()
        square = min(size.width(), size.height())
        self.setFixedSize(square, square)

        # Load in the volume to show, picking one channel:
        self.volume = _IMG_CACHE.getVolume(self.uiState.imagePath)
        data = self.volume[self.uiState._parent.channel]

        c1, c2 = self.uiState.colorLimits
        data = data / np.amax(data)
        data = (data - c1) / (c2 - c1)
        data = util.snapToRange(data, 0.0, 1.0)

        maxSize = np.max(data.shape)

        # Set up OpenGL renderer:
        self.viewWidget = gl.GLViewWidget(self)
        self.viewWidget.orbit(256, 256)
        self.viewWidget.setCameraPosition(0, 0, 0)
        self.viewWidget.opts['distance'] = maxSize * 1.1
        self.viewWidget.show()
        self.viewWidget.setWindowTitle('Volume')
        self.setCentralWidget(self.viewWidget)

        # Optional: Show a grid to help orientate.
        if showGrid:
            g = gl.GLGridItem()
            g.scale(20, 20, 1)
            self.viewWidget.addItem(g)

        # Repeat Z a bunch of times to get approximate scaling
        zRepeat = int(round(data.shape[0] / data.shape[2]))
        data = np.repeat(data, 4, axis=0)
        normalizedData = data * (255./(data.max()/1)) # 0 - 255 scale

        # Colour channels, use greyscale for now.
        d2 = np.empty(data.shape + (4,), dtype=np.ubyte)
        d2[..., 0] = normalizedData
        d2[..., 1] = normalizedData
        d2[..., 2] = normalizedData
        # d2[..., 3] = d2[..., 0]
        d2[..., 3] = (normalizedData.astype(float) / 255.)**4 * 255

        # RGB orientation lines
        d2[:, 0, 0] = [255, 0, 0, 255]
        d2[0, :, 0] = [0, 255, 0, 255]
        d2[0, 0, :] = [0, 0, 255, 255]

        # Finally render into the GL widget:
        v = gl.GLVolumeItem(d2, sliceDensity=1, smooth=False, glOptions='translucent')
        v.translate(-d2.shape[0]/2, -d2.shape[1]/2, -d2.shape[2]/2)
        self.viewWidget.addItem(v)
