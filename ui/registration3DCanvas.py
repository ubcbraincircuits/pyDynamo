import numpy as np

import util

from analysis import addedSubtractedTransitioned, motility

from .baseMatplotlibCanvas import BaseMatplotlibCanvas
from .dendritePainter import colorForBranch
from .dendrogram import calculateAllPositions

MIN_MOTILITY  = 0.1
GREY_COLOUR   = (0.75, 0.75, 0.75, 0.75)
ADDED_COLOR   = (0.00, 1.00, 0.00, 1.00)
GONE_COLOR    = (1.00, 0.00, 0.00, 1.00)
KEPT_COLOR    = (0.00, 0.00, 1.00, 1.00)

# Draws a dendritic tree in 3D space that can be rotated by the user.
class Registration3DCanvas(BaseMatplotlibCanvas):
    def __init__(self, parent, firstTreeIdx, treeModels, filePaths, *args, **kwargs):
        self.firstTree = firstTreeIdx
        self.treeModels = treeModels
        self.filePaths = filePaths

        nPlots = 2 # min(len(treeModels), MAX_TREE_COUNT)
        super(Registration3DCanvas, self).__init__(*args, in3D=True, subplots=nPlots, **kwargs)
        self.fig.canvas.mpl_connect('motion_notify_event', self.handleMove)
        self.fig.subplots_adjust(top=0.95, bottom=0.05, right=0.95, left=0.05, wspace=0.05, hspace=0.05)

    def compute_initial_figure(self):
        xminD, xmaxD, yminD, ymaxD = 0, 0, 0, 0

        # Update colors to be white on black:
        print ("")
        for offset, ax in enumerate(self.axes):
            treeIdx = self.firstTree + offset
            treeModel = self.treeModels[treeIdx]

            otherTreeIdx = treeIdx + (1 if offset == 0 else -1)
            otherTreeModel = self.treeModels[otherTreeIdx]
            changeColor = GONE_COLOR if offset == 0 else ADDED_COLOR

            ax.set_title(util.createTitle(treeIdx, self.filePaths[treeIdx]))
            ax.set_facecolor("white")
            ax.w_xaxis.set_pane_color((1.0,1.0,1.0,1.0))
            ax.w_yaxis.set_pane_color((1.0,1.0,1.0,1.0))
            ax.w_zaxis.set_pane_color((1.0,1.0,1.0,1.0))
            ax.w_xaxis._axinfo['grid'].update({'linewidth':0.25,'color':'gray'})
            ax.w_yaxis._axinfo['grid'].update({'linewidth':0.25,'color':'gray'})
            ax.w_zaxis._axinfo['grid'].update({'linewidth':0.25,'color':'gray'})

            # Draw lines for each branch:
            for branch in treeModel.branches:
                if branch.parentPoint is None:
                    continue
                points = [branch.parentPoint] + branch.points
                x, y, z = treeModel.worldCoordPoints(points)
                ax.plot(x, y, z, c=GREY_COLOUR, lw=1) # TODO - draw axon differently?

            somaColor = None
            otherPointIDs = set([p.id for p in otherTreeModel.flattenPoints()])
            keptPoints, newPoints = [], []
            for p in treeModel.flattenPoints():
                newPoint = p.id not in otherPointIDs
                if p.isRoot():
                    somaColor = changeColor if newPoint else KEPT_COLOR
                else:
                    toAppend = newPoints if newPoint else keptPoints
                    toAppend.append(p)

            # Draw the points by keep/remove:
            if len(keptPoints) > 0:
                x, y, z = treeModel.worldCoordPoints(keptPoints)
                ax.scatter(x, y, z, c=[KEPT_COLOR])
            if len(newPoints) > 0:
                x, y, z = treeModel.worldCoordPoints(newPoints)
                ax.scatter(x, y, z, c=[changeColor])

            # And finally draw the soma as a big sphere (if present):
            if treeModel.rootPoint is not None:
                x, y, z = treeModel.worldCoordPoints([treeModel.rootPoint])
                ax.scatter(x, y, z, c=[somaColor], s=350)

            # Make equal aspect ratio:
            x, y, z = treeModel.worldCoordPoints(treeModel.flattenPoints())
            xmin, xmax = np.min(x), np.max(x)
            ymin, ymax = np.min(y), np.max(y)
            zmin, zmax = np.min(z), np.max(z)
            r = (0.5 * max(xmax - xmin, ymax - ymin, zmax - zmin)) * 1.1
            xM, yM, zM = (xmax + xmin) / 2, (ymax + ymin) / 2, (zmax + zmin) / 2
            ax.set_xlim3d(xM - r, xM + r)
            ax.set_ylim3d(yM - r, yM + r)
            ax.set_zlim3d(zM - r, zM + r)

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
                ax.view_init(elev=eAx.elev, azim=eAx.azim)
                ax.set_xlim3d(event.inaxes.get_xlim3d(), emit=False)
                ax.set_ylim3d(event.inaxes.get_ylim3d(), emit=False)
                ax.set_zlim3d(event.inaxes.get_zlim3d(), emit=False)

    def previous(self, toEnd):
        endIdx = 0
        nextIdx = endIdx if toEnd else max(self.firstTree - 1, endIdx)
        if nextIdx != self.firstTree:
            self.firstTree = nextIdx
            self.needToUpdate()

    def next(self, toEnd):
        endIdx = len(self.treeModels) - 2
        nextIdx = endIdx if toEnd else min(self.firstTree + 1, endIdx)
        if nextIdx != self.firstTree:
            self.firstTree = nextIdx
            self.needToUpdate()


    # def mousePressEvent(self, event):
        # print ("Clicked: (%d %d)" % (event.globalX(), event.globalY()))
        # super(Scatter3DCanvas, self).mousePressEvent(event)
