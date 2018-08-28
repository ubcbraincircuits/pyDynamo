"""
.. module:: imageCache
"""

import numpy as np

from .tiff import tiffRead

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
            return channelImage[uiState._parent.zAxisAt]

    # Returns volume for a tif path, possibly loading it first if not yet cached.
    def getVolume(self, path):
        if path not in self._images:
            imgRaw = tiffRead(path)
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
