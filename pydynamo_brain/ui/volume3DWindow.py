from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.Qt import Qt

import numpy as np
import pyqtgraph.opengl as gl
import scipy.ndimage.filters as filters

import util

_IMG_CACHE = util.ImageCache()

def _interpolateVolume(volume, sizes): # Volume ZXY, sizes XYZ
    # Assume X:Y is 1:1, so X:Z == Y:Z
    if sizes[0] != sizes[1]:
        print ("Volume projection assumes X uM == Y uM")
    initStacks = volume.shape[0]
    zRatio = int(round(sizes[2] / sizes[0]))

    # Step 1: Stretch out with linear interpolation
    expanded = np.repeat(volume, zRatio, axis=0)[zRatio - 1:]
    for i in range(initStacks - 1):
        start, end = i * zRatio, (i + 1) * zRatio
        for offset in range(1, zRatio):
            scale = offset / zRatio
            expanded[start + offset] = scale * expanded[start] + (1 - scale) * expanded[end]

    # Step 2: Gaussian blur
    r = 0.5 # blur sd. radius
    expanded = filters.gaussian_filter(expanded, [zRatio * r, r, r], mode='constant', cval=0)
    return expanded


# Renders the entire volume as 3D voxels using openGL.
class Volume3DWindow(QtWidgets.QMainWindow):
    def __init__(self, parent, uiState, showGrid=False, applyColorLimits=False):
        QtWidgets.QMainWindow.__init__(self, parent)

        self.uiState = uiState

        # Find max height/width size, and take up as much as possible:
        size = QtWidgets.QDesktopWidget().availableGeometry()
        square = min(size.width(), size.height())
        self.setFixedSize(square, square)

        # Load in the volume to show, picking one channel:
        self.volume = _IMG_CACHE.getVolume(self.uiState.imagePath)
        data = self.volume[self.uiState._parent.channel]
        maxSize = np.max(data.shape)

        if applyColorLimits:
            c1, c2 = self.uiState.colorLimits
            data = data / np.amax(data)
            data = (data - c1) / (c2 - c1)
            data = util.snapToRange(data, 0.0, 1.0)

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
        pxlSizes = self.uiState._parent.projectOptions.pixelSizes
        data = _interpolateVolume(data, pxlSizes)
        normalizedData = data * (255./(data.max()/1)) # 0 - 255 scale

        # Colour channels, use greyscale for now.
        GAMMA_CORRECT = 1.5
        d2 = np.empty(data.shape + (4,), dtype=np.ubyte)
        d2[..., 0] = normalizedData
        d2[..., 1] = normalizedData
        d2[..., 2] = normalizedData
        d2[..., 3] = (normalizedData.astype(float) / 255.)**GAMMA_CORRECT * 255

        # RGB orientation lines
        d2[:, 0, 0] = [255, 0, 0, 255]
        d2[0, :, 0] = [0, 255, 0, 255]
        d2[0, 0, :] = [0, 0, 255, 255]

        # Finally render into the GL widget:
        v = gl.GLVolumeItem(d2, sliceDensity=1, smooth=True, glOptions='translucent')
        v.translate(-d2.shape[0]/2, -d2.shape[1]/2, -d2.shape[2]/2)
        self.viewWidget.addItem(v)
