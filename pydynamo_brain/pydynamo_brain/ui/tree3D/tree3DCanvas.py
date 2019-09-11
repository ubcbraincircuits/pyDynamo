import numpy as np

import pydynamo_brain.util as util

from pydynamo_brain.ui.baseMatplotlibCanvas import BaseMatplotlibCanvas
from pydynamo_brain.ui.branchToColorMap import BranchToColorMap

_BRANCH_TO_COLOR_MAP = BranchToColorMap()

# Draws a dendritic tree in 3D space that can be rotated by the user.
class Tree3DCanvas(BaseMatplotlibCanvas):
    TREE_COUNT = 3

    def __init__(self, parent, fullState, firstTreeIdx, treeModels, filePaths, *args, **kwargs):
        self.treeModels = treeModels
        self.filePaths = filePaths
        self.vizTreeCount = min(len(treeModels), self.TREE_COUNT)
        self.firstTree = max(0, min(len(treeModels) - self.vizTreeCount, firstTreeIdx))

        super(Tree3DCanvas, self).__init__(*args, in3D=True, subplots=self.vizTreeCount, **kwargs)
        self.fig.canvas.mpl_connect('motion_notify_event', self.handleMove)
        self.fig.subplots_adjust(top=0.95, bottom=0.05, right=0.95, left=0.05, wspace=0.05, hspace=0.05)

        for ax in self.axes:
            ax.set_facecolor("black")
            ax.w_xaxis.set_pane_color((0.0,0.0,0.0,1.0))
            ax.w_yaxis.set_pane_color((0.0,0.0,0.0,1.0))
            ax.w_zaxis.set_pane_color((0.0,0.0,0.0,1.0))
            ax.w_xaxis._axinfo['grid'].update({'linewidth':0.25,'color':'white'})
            ax.w_yaxis._axinfo['grid'].update({'linewidth':0.25,'color':'white'})
            ax.w_zaxis._axinfo['grid'].update({'linewidth':0.25,'color':'white'})

    def compute_initial_figure(self):
        # Scale results to keep same aspect ratio (matplotlib apsect='equal' is broken in 3d...)
        xmin, xmax, ymin, ymax, zmin, zmax = None, None, None, None, None, None
        for offset, ax in enumerate(self.axes):
            treeIdx = self.firstTree + offset
            treeModel = self.treeModels[treeIdx]
            x, y, z = treeModel.worldCoordPoints(treeModel.flattenPoints())
            if xmin is None:
                xmin, xmax = np.min(x), np.max(x)
                ymin, ymax = np.min(y), np.max(y)
                zmin, zmax = np.min(z), np.max(z)
            else:
                xmin, xmax = min(xmin, np.min(x)), max(xmax, np.max(x))
                ymin, ymax = min(ymin, np.min(y)), max(ymax, np.max(y))
                zmin, zmax = min(zmin, np.min(z)), max(zmax, np.max(z))

        r = (0.5 * max(xmax - xmin, ymax - ymin, zmax - zmin)) * 1.1
        xM, yM, zM = (xmax + xmin) / 2, (ymax + ymin) / 2, (zmax + zmin) / 2

        for offset, ax in enumerate(self.axes):
            treeIdx = self.firstTree + offset
            treeModel = self.treeModels[treeIdx]
            ax.set_title(util.createTitle(treeIdx, self.filePaths[treeIdx]), color='white')
            ax.set_xlim3d(xM - r, xM + r)
            ax.set_ylim3d(yM - r, yM + r)
            ax.set_zlim3d(zM - r, zM + r)
            self.drawSingleTree3D(ax, treeIdx, treeModel)

    def drawSingleTree3D(self, ax, treeIdx, treeModel):
        # No tree, draw nothing...
        if treeModel is None or treeModel.rootPoint is None:
            return

        # Draw each branch in the same color as in the flat version:
        for i, branch in enumerate(treeModel.branches):
            if branch.parentPoint is None:
                continue
            points = [branch.parentPoint] + branch.points
            x, y, z = treeModel.worldCoordPoints(points)
            ax.plot(x, y, z, c=_BRANCH_TO_COLOR_MAP.rgbForBranch(i))

        # And finally draw the soma as a big sphere:
        x, y, z = treeModel.worldCoordPoints([treeModel.rootPoint])
        ax.scatter(x, y, z, c=_BRANCH_TO_COLOR_MAP.rgbForBranch(0), s=100)

    def needToUpdate(self):
        for ax in self.axes:
            ax.cla()
        self.compute_initial_figure()
        self.draw()

    def handleMove(self, event):
        eAx = event.inaxes
        if event.inaxes in self.axes:
            for ax in self.axes:
                if ax == event.inaxes:
                    continue
                else:
                    ax.view_init(elev=eAx.elev, azim=eAx.azim)
                    ax.set_xlim3d(event.inaxes.get_xlim3d(), emit=False)
                    ax.set_ylim3d(event.inaxes.get_ylim3d(), emit=False)
                    ax.set_zlim3d(event.inaxes.get_zlim3d(), emit=False)

    def canPrev(self):
        return self.firstTree > 0

    def canNext(self):
        return self.firstTree < len(self.treeModels) - self.vizTreeCount

    def previous(self, toEnd):
        endIdx = 0
        nextIdx = endIdx if toEnd else max(self.firstTree - 1, endIdx)
        if nextIdx != self.firstTree:
            self.firstTree = nextIdx
            self.needToUpdate()

    def next(self, toEnd):
        endIdx = len(self.treeModels) - self.vizTreeCount
        nextIdx = endIdx if toEnd else min(self.firstTree + 1, endIdx)
        if nextIdx != self.firstTree:
            self.firstTree = nextIdx
            self.needToUpdate()
