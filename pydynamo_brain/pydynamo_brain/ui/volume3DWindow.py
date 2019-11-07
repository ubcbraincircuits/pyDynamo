import PyQt5.QtCore # Needs to be before napari
import napari
import numpy as np

import pydynamo_brain.util as util
from pydynamo_brain.util.nearTreeMasking import maskedNearTree

_IMG_CACHE = util.ImageCache()

class Volume3DWindow():
    def __init__(self, parent, uiState):
        self.uiState = uiState

        # Load in the volume to show, picking one channel:
        self.volume = _IMG_CACHE.getVolume(self.uiState.imagePath)

    # @return Napari viewer position, for a given tree location
    def locationToZYXList(self, location, zyxScale):
        # XYZ -> ZYX
        location = list(location)[::-1]
        return [location[0] * zyxScale[0], location[1] * zyxScale[1], location[2] * zyxScale[2]]

    # @return Numpy list for the path along a branch, in napari space.
    def branchToPath(self, branch, zyxScale):
        if branch.parentPoint is None:
            return []
        path = [ self.locationToZYXList(branch.parentPoint.location, zyxScale) ]
        for p in branch.points:
            path.append(self.locationToZYXList(p.location, zyxScale))
        return np.array(path)

    # @return Numpy list of paths in the tree, one for each branch.
    def treeToPaths(self, tree, zyxScale):
        paths = []
        for b in tree.branches:
            branchPath = self.branchToPath(b, zyxScale)
            if len(branchPath) > 1:
                paths.append(np.array(branchPath))
        return np.array(paths)

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

            if self.uiState._tree is not None and len(self.uiState._tree.flattenPoints()) > 1:
                maskedVolume = maskedNearTree(self.volume, self.uiState._tree, xyzScale)
                for c in reversed(range(maskedVolume.shape[0])):
                    name = 'Masked Volume'
                    if maskedVolume.shape[0] > 1:
                        name = '%s (%d)' % (name, c + 1)
                    layer = viewer.add_image(maskedVolume[c], name=name, rgb=False)
                    layer.scale = zyxScale
                    layer.contrast_limits = [cl * 255 for cl in self.uiState.colorLimits]
                    layer.visible = False

            viewer.dims.ndim = 3
            viewer.dims.ndisplay = 3

            # Add a layer representing the tree
            paths = self.treeToPaths(self.uiState._tree, zyxScale)
            viewer.add_shapes(
                paths, shape_type='path',
                name='Arbor',
                edge_width=0.3,
                edge_color='blue',
            )
