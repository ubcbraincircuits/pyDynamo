import PyQt5.QtCore # Needs to be before napari
import napari
import numpy as np

import pydynamo_brain.util as util

_IMG_CACHE = util.ImageCache()

class Volume3DWindow():
    def __init__(self, parent, uiState):
        self.uiState = uiState

        # Load in the volume to show, picking one channel:
        volume = _IMG_CACHE.getVolume(self.uiState.imagePath)

        # TODO: Add one layer per channel
        self.data = volume[self.uiState._parent.channel]
        print (self.data.shape)

    def show(self):
        with napari.gui_qt():
            viewer = napari.view_image(self.data, name='Volume', rgb=False)
            xyzScale = self.uiState._parent.projectOptions.pixelSizes
            zyxScale = [1, xyzScale[1] / xyzScale[2], xyzScale[0] / xyzScale[2]]
            viewer.layers['Volume'].scale = zyxScale

            viewer.layers['Volume'].contrast_limits = [cl * 255 for cl in self.uiState.colorLimits]
            viewer.dims.ndim = 3
            viewer.dims.ndisplay = 3

            # TODO: Add shape layer for drawing
            # viewer.layers['Shapes'].add(y, shape_type='rectangle')
