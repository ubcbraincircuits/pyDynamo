import PyQt5.QtCore # Needs to be before napari
import napari
import numpy as np

import pydynamo_brain.util as util

_IMG_CACHE = util.ImageCache()

class Volume3DWindow():
    def __init__(self, parent, uiState):
        self.uiState = uiState

        # Load in the volume to show, picking one channel:
        self.volume = _IMG_CACHE.getVolume(self.uiState.imagePath)

    def show(self):
        xyzScale = self.uiState._parent.projectOptions.pixelSizes
        zyxScale = [1, xyzScale[1] / xyzScale[2], xyzScale[0] / xyzScale[2]]

        with napari.gui_qt():
            viewer = napari.Viewer()
            for c in reversed(range(self.volume.shape[0])):
                name = 'Volume'
                if self.volume.shape[0] > 1:
                    name = '%s (%d)' % (name, c + 1)
                layer = viewer.add_image(self.volume[c], name=name, rgb=False)
                layer.scale = zyxScale
                layer.contrast_limits = [cl * 255 for cl in self.uiState.colorLimits]
                layer.visible = (c == self.uiState._parent.channel)

            viewer.dims.ndim = 3
            viewer.dims.ndisplay = 3

            # TODO: Add shape layer for drawing
            # viewer.layers['Shapes'].add(y, shape_type='rectangle')
