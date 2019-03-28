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

        nPlots = 3 # min(len(treeModels), MAX_TREE_COUNT)
        super(Registration3DCanvas, self).__init__(*args, in3D=True, subplots=nPlots, **kwargs)
        self.fig.canvas.mpl_connect('motion_notify_event', self.handleMove)
        self.fig.subplots_adjust(top=0.95, bottom=0.05, right=0.95, left=0.05, wspace=0.05, hspace=0.05)

    def compute_initial_figure(self):
        xminD, xmaxD, yminD, ymaxD = 0, 0, 0, 0

        # Update colors to be white on black:
        print ("")
        for offset, ax in enumerate(self.axes):
            ax.set_facecolor("white")
            ax.w_xaxis.set_pane_color((1.0,1.0,1.0,1.0))
            ax.w_yaxis.set_pane_color((1.0,1.0,1.0,1.0))
            ax.w_zaxis.set_pane_color((1.0,1.0,1.0,1.0))
            ax.w_xaxis._axinfo['grid'].update({'linewidth':0.25,'color':'gray'})
            ax.w_yaxis._axinfo['grid'].update({'linewidth':0.25,'color':'gray'})
            ax.w_zaxis._axinfo['grid'].update({'linewidth':0.25,'color':'gray'})

            if offset == 0 or offset == 1:
                self.drawSingleTreeChanges(ax, offset == 0)
            else:
                self.drawPointMapping(ax)

    # Given one tree, draw the points that stay in blue, and the points that don't
    # exist in the other tree in red (if removed) or green (if added)
    def drawSingleTreeChanges(self, ax, isFirstTree):
        changeColor = GONE_COLOR if isFirstTree else ADDED_COLOR

        treeIdx = self.firstTree + (0 if isFirstTree else 1)
        otherTreeIdx = self.firstTree + (1 if isFirstTree else 0)
        treeModel = self.treeModels[treeIdx]
        otherTreeModel = self.treeModels[otherTreeIdx]

        ax.set_title(util.createTitle(treeIdx, self.filePaths[treeIdx]))

        # Draw lines for each branch:
        for branch in treeModel.branches:
            if branch.parentPoint is None:
                continue
            points = [branch.parentPoint] + branch.points
            x, y, z = treeModel.worldCoordPoints(points)
            ax.plot(x, y, z, c=GREY_COLOUR, lw=1) # TODO - draw axon differently?

        # Split points by keep/new status:
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
        self.drawPointsOneColor(ax, treeModel, keptPoints, KEPT_COLOR)
        self.drawPointsOneColor(ax, treeModel, newPoints, changeColor)
        self.drawPointsOneColor(ax, treeModel, [treeModel.rootPoint], somaColor, s=350) # Big soma

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

    # For each point, draw the old and new position, connected
    def drawPointMapping(self, ax):
        ax.set_title("Point mapping")

        treeA, treeB = self.treeModels[self.firstTree], self.treeModels[self.firstTree + 1]
        treeAPoints, treeBPoints = {}, {}
        for p in treeA.flattenPoints():
            treeAPoints[p.id] = p
        for p in treeB.flattenPoints():
            treeBPoints[p.id] = p
        aIDs, bIDs = set(treeAPoints.keys()), set(treeBPoints.keys())
        onlyA, onlyB, both = aIDs - bIDs, bIDs - aIDs, aIDs & bIDs

        delta = (0, 0, 0)
        for i in both:
            # HACK: aX vs ax
            aX, ay, az = treeA.worldCoordPoints([treeAPoints[i]])
            bx, by, bz = treeB.worldCoordPoints([treeBPoints[i]])
            delta = (
                np.mean(np.array(aX)) - np.mean(np.array(bx)),
                np.mean(np.array(ay)) - np.mean(np.array(by)),
                np.mean(np.array(az)) - np.mean(np.array(bz))
            )

        onlyAPoints = [treeAPoints[i] for i in onlyA]
        onlyBPoints = [treeBPoints[i] for i in onlyB]
        self.drawPointsOneColor(ax, treeA, onlyAPoints, GONE_COLOR)
        self.drawPointsOneColor(ax, treeB, onlyBPoints, ADDED_COLOR, delta=delta)
        for i in both:
            # HACK: aX vs ax
            aX, ay, az = treeA.worldCoordPoints([treeAPoints[i]])
            aX, ay, az = aX[0], ay[0], az[0]
            bx, by, bz = treeB.worldCoordPoints([treeBPoints[i]])
            bx, by, bz = bx[0] + delta[0], by[0] + delta[1], bz[0] + delta[2]
            ax.scatter([aX, bx], [ay, by], [az, bz], c=[KEPT_COLOR])
            ax.plot([aX, bx], [ay, by], [az, bz], c=GREY_COLOUR, lw=1)

    def drawPointsOneColor(self, ax, treeModel, points, color, delta=(0, 0, 0), **kwargs):
        if len(points) > 0:
            x, y, z = treeModel.worldCoordPoints(points)
            x = [v + delta[0] for v in x]
            y = [v + delta[1] for v in y]
            z = [v + delta[2] for v in z]
            ax.scatter(x, y, z, c=[color], **kwargs)

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
