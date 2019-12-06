import PyQt5.QtCore # Needs to be before napari
import napari
import numpy as np

import pydynamo_brain.util as util
from pydynamo_brain.util.nearTreeMasking import maskedNearTree

_IMG_CACHE = util.ImageCache()

from .branchToColorMap import BranchToColorMap
_BRANCH_TO_COLOR_MAP = BranchToColorMap()

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

    # @return (data, width, color) for a line segment between two points
    def segmentToShape(self, prevPoint, nextPoint, zyxScale, color):
        width = 0.3
        if prevPoint.radius is None:
            width = nextPoint.radius
        elif nextPoint.radius is None:
            width = prevPoint.radius
        elif prevPoint.radius is not None and nextPoint.radius is not None:
            width = (prevPoint.radius + nextPoint.radius) / 2.0

        path = [
            self.locationToZYXList(prevPoint.location, zyxScale),
            self.locationToZYXList(nextPoint.location, zyxScale)
        ]
        return (path, width, color)

    # @return list of (data, width, color) for each shape in the branch
    def branchToShapes(self, branch, zyxScale):
        if branch.parentPoint is None:
            return []
        color = list(_BRANCH_TO_COLOR_MAP.rgbForBranch(branch))
        shapes = []
        prevPoint = branch.parentPoint
        for nextPoint in branch.points:
            shapes.append(self.segmentToShape(prevPoint, nextPoint, zyxScale, color))
            prevPoint = nextPoint
        return shapes

    # @return list of (data, width, color) for each shape in the tree
    def treeToShapes(self, tree, zyxScale):
        # data, width, color
        shapes = []
        for b in tree.branches:
            branchShapes = self.branchToShapes(b, zyxScale)
            if len(branchShapes) > 0:
                shapes.extend(branchShapes)
        return shapes

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

            # Note: Addition of near-tree volume is removed for now as it is slow.
            # Uncomment to add back in, there may eventually be an option in the UI
            """
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
            """

            viewer.dims.ndim = 3
            viewer.dims.ndisplay = 3

            # Add shapes representing the tree
            pathShapes = self.treeToShapes(self.uiState._tree, zyxScale)
            shapeLayer = None
            for data, width, color in pathShapes:
                if shapeLayer is None:
                    shapeLayer = viewer.add_shapes(
                        data, shape_type='path',
                        name='Arbor',
                        edge_width=width,
                        edge_color=color,
                    )
                else:
                    shapeLayer.add(
                        data, shape_type='path',
                        edge_width=width,
                        edge_color=color,
                    )
