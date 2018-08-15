import numpy as np

import util

from analysis import addedSubtractedTransitioned, motility

from .baseMatplotlibCanvas import BaseMatplotlibCanvas
from .dendritePainter import colorForBranch

MIN_MOTILITY  = 0.1
GREY_COLOUR   = (0.75, 0.75, 0.75, 1.00)
ADDED_COLOR   = (0.00, 1.00, 0.00, 0.75)
TRANS_COLOR   = (0.00, 0.00, 0.00, 0.00) # Not shown ?! TODO: verify
GROW_COLOR    = (0.00, 1.00, 1.00, 0.75)
SHRINK_COLOR  = (1.00, 0.00, 1.00, 0.75)
GONE_COLOR    = (1.00, 0.00, 0.00, 0.75)
RETRACT_COLOR = (1.00, 1.00, 0.00, 0.75)

# Draws a dendritic tree in 3D space that can be rotated by the user.
class Motility3DCanvas(BaseMatplotlibCanvas):
    def __init__(self, parent, treeModels, opt, sizeFactor=10, *args, **kwargs):
        self.treeModels = treeModels
        self.options = opt
        np.set_printoptions(precision=3)

        self.branchIDList = util.sortedBranchIDList(self.treeModels)
        _, self.added, self.subtracted, self.transitioned, _, _ = addedSubtractedTransitioned(
            self.treeModels,
            excludeAxon=opt.excludeAxon, excludeBasal=opt.excludeBasal,
            terminalDist=opt.terminalDist, filoDist=opt.filoDist
        )
        mot, self.filoLengths = motility(
            self.treeModels,
            excludeAxon=opt.excludeAxon, excludeBasal=opt.excludeBasal, includeAS=opt.includeAS,
            terminalDist=opt.terminalDist, filoDist=opt.filoDist
        )
        np.set_printoptions()
        self.motility = mot['raw']
        self.sizeFactor = sizeFactor

        super(Motility3DCanvas, self).__init__(*args, in3D=True, subplots=len(treeModels), **kwargs)
        self.fig.canvas.mpl_connect('motion_notify_event', self.handleMove)
        # TODO: Use landmarks for mean shifting

    def compute_initial_figure(self):
        SZ_FACTOR = self.sizeFactor

        # Update colors to be white on black:
        for treeIdx, ax in enumerate(self.axes):
            treeModel = self.treeModels[treeIdx]
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
                ax.plot(x, y, z, c=GREY_COLOUR) # TODO - draw axon differently?

            # Draw filo for each branch:
            if treeIdx > 0:
                oldTreeModel = self.treeModels[treeIdx - 1]

                # For debugging puposes, maybe remove?
                growCount, shrinkCount = 0, 0

                for branch in treeModel.branches:
                    branchIdx = self.branchIDList.index(branch.id)

                    plot = True
                    if self.added[treeIdx-1][branchIdx]:
                        color, sz = ADDED_COLOR, self.filoLengths[treeIdx][branchIdx] * SZ_FACTOR
                    elif self.transitioned[treeIdx-1][branchIdx]:
                        color, sz = TRANS_COLOR, self.filoLengths[treeIdx][branchIdx] * SZ_FACTOR
                        plot = False # Don't draw transitions ?!
                    else:
                        mot = self.motility[treeIdx-1][branchIdx]
                        if abs(mot) > MIN_MOTILITY and len(branch.points) > 0:
                            color = GROW_COLOR if mot > 0 else SHRINK_COLOR
                            if mot > 0:
                                growCount += 1
                            else:
                                shrinkCount += 1
                            sz = abs(mot) * SZ_FACTOR
                        else:
                            plot = False
                    if plot:
                        if len(branch.points) != 0 :
                            x, y, z = treeModel.worldCoordPoints([branch.points[-1]])
                            ax.scatter(x, y, z, c=color, s=sz)

                    # Show removed branches from last point:
                    branchInLast = self.treeModels[treeIdx - 1].getBranchByID(branch.id)
                    if branchInLast is not None:
                        for childPoint in branchInLast.points:
                            retracted = 0
                            for childBranch in childPoint.children:
                                if childBranch is None or len(childBranch.points) == 0:
                                    continue
                                childBranchIdx = self.branchIDList.index(childBranch.id)

                                firstPointID = childBranch.points[0].id
                                inCurrentTree = self.treeModels[treeIdx].getPointByID(firstPointID) is not None
                                if not inCurrentTree:
                                    retracted += self.filoLengths[treeIdx - 1][childBranchIdx]
                            if retracted > 0:
                                x, y, z = oldTreeModel.worldCoordPoints([childPoint])
                                childPointInNew = treeModel.getPointByID(childPoint.id)
                                if childPointInNew is not None:
                                    x, y, z = treeModel.worldCoordPoints([childPointInNew])
                                # print ("extra retraction: " + str(retracted))
                                ax.scatter(x, y, z, c=RETRACT_COLOR, s=(retracted * SZ_FACTOR))
                        if self.subtracted[treeIdx - 1][branchIdx]:
                            # Draw at the parent of the subtracted branch, not the end point.
                            drawAt = branchInLast.parentPoint
                            if drawAt is not None:
                                # print ("extra subtraction: " + str(retracted))
                                sz = self.filoLengths[treeIdx-1][branchIdx] * SZ_FACTOR
                                x, y, z = oldTreeModel.worldCoordPoints([drawAt])
                                drawAtInNew = treeModel.getPointByID(drawAt.id)
                                if drawAtInNew is not None:
                                    x, y, z = treeModel.worldCoordPoints([drawAtInNew])
                                ax.scatter(x, y, z, c=GONE_COLOR, s=sz)

                # For debugging puposes, maybe remove?
                print ("Stack #%d -> #%d" % (treeIdx, treeIdx + 1))
                print ("  - #Added        = %d" % np.sum(self.added[treeIdx-1]))
                print ("  - #Subtracted   = %d" % np.sum(self.subtracted[treeIdx-1]))
                print ("  - #Transitioned = %d" % np.sum(self.transitioned[treeIdx-1]))
                print ("  - #Grown        = %d" % growCount)
                print ("  - #Shrunk       = %d" % shrinkCount)

            # And finally draw the soma as a big sphere (if present):
            if treeModel.rootPoint is not None:
                x, y, z = treeModel.worldCoordPoints([treeModel.rootPoint])
                ax.scatter(x, y, z, c=GREY_COLOUR, s=350)

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


    # def mousePressEvent(self, event):
        # print ("Clicked: (%d %d)" % (event.globalX(), event.globalY()))
        # super(Scatter3DCanvas, self).mousePressEvent(event)
