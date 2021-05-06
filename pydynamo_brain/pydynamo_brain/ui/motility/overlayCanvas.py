import matplotlib
import matplotlib.pyplot as plt

import numpy as np
import numpy.polynomial.polynomial as npPoly

import skimage.transform as skimgTransform
from skimage.registration import phase_cross_correlation
from skimage.filters import gaussian

import pydynamo_brain.util as util


from pydynamo_brain.ui.baseMatplotlibCanvas import BaseMatplotlibCanvas

GREY_COLOUR   = (0.75, 0.75, 0.75, 0.75)

# Draws a dendritic tree in 3D space that can be rotated by the user.
class OverlayCanvas(BaseMatplotlibCanvas):

    def __init__(self, parent, fullState, windowIndex, *args, **kwargs):
        print("Window Index:", windowIndex)
        self.fullState = fullState
        self.overlayViewWindow = parent
        self.windowIndex = windowIndex
        super(OverlayCanvas, self).__init__(parent, *args, in3D=False, **kwargs)

        self.fig.subplots_adjust(top=0.95, bottom=0.2, right=0.95, left=0.2, wspace=0.05, hspace=0.05)

    def _simpleNorm(self, img, gamma=1.0):
        mn = np.min(img)
        qt = 0.995
        mx = np.quantile(img.ravel(), qt)
        img = img.clip(mn, mx)
        return ((img - mn) / (mx - mn))

    def buildSlices(self, dn, n):
        if dn == 0:
            return slice(0, n), slice(0, n)
        elif dn > 0:
            return slice(dn, n), slice(0, n - dn)
        elif dn < 0:
            return slice(0, n + dn), slice(0 - dn, n)

    def compute_initial_figure(self):
        ax  = self.axes[0]
        IMAGE_CACHE =util.ImageCache()

        img = [IMAGE_CACHE.getVolume(fp) for fp in self.fullState.filePaths]
        img0 = img[self.windowIndex-1][0, ...]
        img1 = img[self.windowIndex][0, ...]

        img0 = gaussian(img0, .5)
        img1 = gaussian(img1, .5)

        img0 = self._simpleNorm(img0, 1.1)
        img1 = self._simpleNorm(img1, 1.1)

        p0Stack = img0.max(axis=0) ** 1.2
        p1Stack = img1.max(axis=0) ** 1.2
        p1Stack = skimgTransform.rotate(p1Stack, angle=0.85)

        shift = np.array(phase_cross_correlation(p0Stack, p1Stack, upsample_factor=1, return_error=False))

        dY, dX = int(round(shift[0])), int(round(shift[1]))
        sliceY1, sliceY2 = self.buildSlices(dY, p1Stack.shape[0])
        sliceX1, sliceX2 = self.buildSlices(dX, p1Stack.shape[1])
        shifted = np.zeros(p1Stack.shape)
        shifted[sliceY1, sliceX1] = p1Stack[sliceY2, sliceX2]
        p1Stack = shifted

        mergedStack = p0Stack
        mergedStack = np.zeros((p0Stack.shape[0], p0Stack.shape[1], 3))
        mergedStack[:, :, 0] = p0Stack
        mergedStack[:, :, 1] = p1Stack
        mergedStack[:, :, 2] = np.minimum(p0Stack, p1Stack)

        ax.get_xaxis().set_visible(False)
        ax.get_yaxis().set_visible(False)
        ax.set_aspect('equal')
        ax.imshow(mergedStack)
