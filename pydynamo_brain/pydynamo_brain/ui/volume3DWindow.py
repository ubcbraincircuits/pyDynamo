import napari
import numpy as np

import pydynamo_brain.util as util

_IMG_CACHE = util.ImageCache()

class Volume3DWindow():
    def __init__(self, parent, uiState):
        self.uiState = uiState

        # Load in the volume to show, picking one channel:
        volume = _IMG_CACHE.getVolume(self.uiState.imagePath)
        self.data = volume[self.uiState._parent.channel]

    def show(self):
        with napari.gui_qt():
            viewer = napari.view_image(self.data, name='Volume', rgb=False)
            viewer.layers['Volume'].contrast_limits = [cl * 255 for cl in self.uiState.colorLimits]
            viewer.dims.ndim = 3
            viewer.dims.ndisplay = 3
