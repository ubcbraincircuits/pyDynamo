"""
.. module:: imageCache
"""

import numpy as np
from tifffile import TiffFile

import util

# libtiff.libtiff_ctypes.suppress_warnings()

def tiffRead(path, verbose=True):
    # First use tifffile to get channel data (not supported by libtiff?)
    shape, stack = None, None
    with TiffFile(path) as tif:
        shape = tif.asarray().shape
        stack = tif.asarray()
    nChannels = shape[0] if len(shape) == 4 else 1
    if verbose:
        print ("Loaded TIF, shape: %s" % str(shape))

    if len(shape) == 3:
        # HACK - colours have been merged?
        if stack.shape[0] % 2 == 0 and stack.shape[0] > 100:
            sz = stack.shape[0] // 2
            stack = np.array([
                stack[:sz, :, :],
                stack[sz:, :, :]
            ])
        else:
            stack = np.expand_dims(stack, axis=0)

    # stack = np.swapaxes(stack, 1, 2)
    return stack


class ImageCache:
    """Singleton cache mapping .tif file path to Image volumes.

    Used so that the Full UI States can store just paths, and volumes are not copied around
    or saved to file/history.
    """

    # Singleton instance - create ImageCache() and get back the same cache each time.
    _instance = None
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = object.__new__(ImageCache)
        return cls._instance

    # Maps path string -> loaded 4D (c, z, y, x) Volume
    _images = dict()

    # Call this when a state has its path changed - preloads, and updates shape information.
    def handleNewUIState(self, uiState):
        volume = self.getVolume(uiState.imagePath)
        uiState._parent.updateVolumeSize(volume.shape)

    # Get the current 2D image for a state, using the full state's current channel and Z axis
    def imageForUIState(self, uiState):
        channelImage = self.getVolume(uiState.imagePath)[uiState._parent.channel]
        if uiState.zProject:
            return np.amax(channelImage, axis=0)
        else:
            zAt = util.zStackForUiState(uiState)
            if zAt < 0 or zAt >= channelImage.shape[0]:
                return np.zeros(channelImage[0].shape)
            return channelImage[zAt]

    # Returns volume for a tif path, possibly loading it first if not yet cached.
    def getVolume(self, path, verbose=True):
        if path not in self._images:
            imgRaw = tiffRead(path, verbose)
            imgClean = self._postProcess(imgRaw)
            self._images[path] = imgClean
        return self._images[path]

    # Applies post-processing to a loaded tiff - gamma correct, scale, and convert to uint8
    def _postProcess(self, image):
        image = image.astype(np.float64) ** 0.8 # Gamma correction
        for c in range(image.shape[0]):
            for i in range(image.shape[1]):
                d = image[c, i]
                mn = np.percentile(d, 10)
                mx = np.max(d)
                image[c, i] = 255 * (d - mn) / (mx - mn)
        return np.round(image.clip(min=0)).astype(np.uint8)

    # Estimate the channel count by using the first loaded image,
    #   or loading a new one if there is none.
    def estimateChannelCount(self, fullState):
        for imgPath in fullState.filePaths:
            if imgPath in self._images:
                return self._images[imgPath].shape[0]
        if len(fullState.filePaths) == 0:
            return 1
        return self.getVolume(fullState.filePaths[0]).shape[0]
