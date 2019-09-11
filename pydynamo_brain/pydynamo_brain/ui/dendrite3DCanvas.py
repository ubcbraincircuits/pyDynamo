import numpy as np

from .baseMatplotlibCanvas import BaseMatplotlibCanvas
from .branchToColorMap import BranchToColorMap

_BRANCH_TO_COLOR_MAP = BranchToColorMap()

# Draws a dendritic tree in 3D space that can be rotated by the user.
class Dendrite3DCanvas(BaseMatplotlibCanvas):
    def __init__(self, treeModel, *args, **kwargs):
        self.treeModel = treeModel
        super(Dendrite3DCanvas, self).__init__(*args, in3D=True, **kwargs)

    def compute_initial_figure(self):
        ax = self.axes[0]
        # Update colors to be white on black:
        ax.set_facecolor("black")
        ax.w_xaxis.set_pane_color((0.0,0.0,0.0,1.0))
        ax.w_yaxis.set_pane_color((0.0,0.0,0.0,1.0))
        ax.w_zaxis.set_pane_color((0.0,0.0,0.0,1.0))
        ax.w_xaxis._axinfo['grid'].update({'linewidth':0.25,'color':'white'})
        ax.w_yaxis._axinfo['grid'].update({'linewidth':0.25,'color':'white'})
        ax.w_zaxis._axinfo['grid'].update({'linewidth':0.25,'color':'white'})

        # No tree, draw nothing...
        if self.treeModel is None or self.treeModel.rootPoint is None:
            return

        # Draw each branch in the same color as in the flat version:
        for i, branch in enumerate(self.treeModel.branches):
            if branch.parentPoint is None:
                continue
            points = [branch.parentPoint] + branch.points
            x, y, z = self.treeModel.worldCoordPoints(points)
            ax.plot(x, y, z, c=_BRANCH_TO_COLOR_MAP.rgbForBranch(i))

        # And finally draw the soma as a big sphere:
        x, y, z = self.treeModel.worldCoordPoints([self.treeModel.rootPoint])
        ax.scatter(x, y, z, c=_BRANCH_TO_COLOR_MAP.rgbForBranch(0), s=100)

        # Scale results to keep same aspect ratio (matplotlib apsect='equal' is broken in 3d...)
        x, y, z = self.treeModel.worldCoordPoints(self.treeModel.flattenPoints())
        xmin, xmax = np.min(x), np.max(x)
        ymin, ymax = np.min(y), np.max(y)
        zmin, zmax = np.min(z), np.max(z)
        r = (0.5 * max(xmax - xmin, ymax - ymin, zmax - zmin)) * 1.1
        xM, yM, zM = (xmax + xmin) / 2, (ymax + ymin) / 2, (zmax + zmin) / 2
        ax.set_xlim3d(xM - r, xM + r)
        ax.set_ylim3d(yM - r, yM + r)
        ax.set_zlim3d(zM - r, zM + r)

    def needToUpdate(self):
        self.axes[0].cla()
        self.compute_initial_figure()
        self.draw()

    # def mousePressEvent(self, event):
        # print ("Clicked: (%d %d)" % (event.globalX(), event.globalY()))
        # super(Scatter3DCanvas, self).mousePressEvent(event)
