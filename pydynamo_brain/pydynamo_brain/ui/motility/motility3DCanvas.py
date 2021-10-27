import numpy as np

from pydynamo_brain.analysis import addedSubtractedTransitioned, motility
from pydynamo_brain.ui.baseMatplotlibCanvas import BaseMatplotlibCanvas
from pydynamo_brain.ui.dendrogram import calculateAllPositions
import pydynamo_brain.util as util

GREY_COLOUR   = (0.75, 0.75, 0.75, 1.00)
TREE_COLOUR   = (0.60, 0.60, 0.60, 1.00)
ADDED_COLOR   = (0.00, 1.00, 0.00, 0.75)
TRANS_COLOR   = (0.00, 0.00, 0.00, 0.00) # Not shown ?! TODO: verify
GROW_COLOR    = (0.00, 1.00, 1.00, 0.75)
SHRINK_COLOR  = (1.00, 0.00, 1.00, 0.75)
GONE_COLOR    = (1.00, 0.00, 0.00, 0.75)
RETRACT_COLOR = (1.00, 1.00, 0.00, 0.75)

MAX_TREE_COUNT = 3 # Only show this many trees, scroll to the others.

# Draws a dendritic tree in 3D space that can be rotated by the user.
class Motility3DCanvas(BaseMatplotlibCanvas):
    def __init__(self, parent, selectedTree, treeModels, is2D, filePaths, opt, sizeFactor=10, *args, **kwargs):
        self.firstTree = max(0, min(selectedTree - 1, len(treeModels) - MAX_TREE_COUNT))
        self.treeModels = treeModels
        self.filePaths = filePaths
        self.options = opt
        self.dendrogram = is2D
        np.set_printoptions(precision=3)

        self.branchIDList = util.sortedBranchIDList(self.treeModels)
        self.filoTypes, self.added, self.subtracted, self.transitioned, _, _ = addedSubtractedTransitioned(
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

        self.dendrogramX, self.dendrogramY = calculateAllPositions(
            self.treeModels, self.filoTypes, self.branchIDList, filoDist=opt.filoDist
        )

        nPlots = min(len(treeModels), MAX_TREE_COUNT)
        super(Motility3DCanvas, self).__init__(*args, in3D=(not self.dendrogram), subplots=nPlots, **kwargs)
        self.fig.canvas.mpl_connect('motion_notify_event', self.handleMove)
        self.fig.subplots_adjust(top=0.95, bottom=0.05, right=0.95, left=0.05, wspace=0.05, hspace=0.05)

    def compute_initial_figure(self):
        SZ_FACTOR = self.sizeFactor

        xminD, xmaxD, yminD, ymaxD = 0, 0, 0, 0
        if self.dendrogram:
            allX = [x for treeX in self.dendrogramX for x in treeX.values()]
            allY = [y for treeY in self.dendrogramY for y in treeY.values()]
            xminD, xmaxD = np.min(allX), np.max(allX)
            yminD, ymaxD = np.min(allY), np.max(allY)

        # Update colors to be white on black:
        print ("")
        for offset, ax in enumerate(self.axes):
            treeIdx = self.firstTree + offset
            treeModel = self.treeModels[treeIdx]
            denX, denY = self.dendrogramX[treeIdx], self.dendrogramY[treeIdx]
            ax.set_title(util.createTitle(treeIdx, self.filePaths[treeIdx]))
            ax.set_facecolor("white")
            if self.dendrogram:
                ax.margins(0.1)
                ax.set_xticklabels([])
                ax.set_yticklabels([])
            else:
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
                if self.dendrogram:
                    x = [denX[p.id] for p in points]
                    y = [denY[p.id] for p in points]
                    ax.plot(x, y, c=TREE_COLOUR)
                else:
                    x, y, z = treeModel.worldCoordPoints(points)
                    ax.plot(x, y, z, c=TREE_COLOUR) # TODO - draw axon differently?

            # Draw filo for each branch:
            if treeIdx > 0:
                oldTreeModel = self.treeModels[treeIdx - 1]
                oldDenX, oldDenY = self.dendrogramX[treeIdx - 1], self.dendrogramY[treeIdx - 1]

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
                        if abs(mot) >= self.options.minMotilityDist and len(branch.points) > 0:
                            color = GROW_COLOR if mot > 0 else SHRINK_COLOR
                            if mot > 0:
                                growCount += 1
                            else:
                                shrinkCount += 1
                            sz = abs(mot) * SZ_FACTOR
                        else:
                            plot = False
                    if plot:
                        if len(branch.points) != 0:
                            if self.dendrogram:
                                x = [denX[branch.points[-1].id]]
                                y = [denY[branch.points[-1].id]]
                                ax.scatter(x, y, c=[color], s=sz)
                            else:
                                x, y, z = treeModel.worldCoordPoints([branch.points[-1]])
                                ax.scatter(x, y, z, c=[color], s=sz)

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
                                # print ("extra retraction: " + str(retracted))
                                if self.dendrogram:
                                    # Not really correct...
                                    pass
                                else:
                                    x, y, z = oldTreeModel.worldCoordPoints([childPoint])
                                    childPointInNew = treeModel.getPointByID(childPoint.id)
                                    if childPointInNew is not None:
                                        x, y, z = treeModel.worldCoordPoints([childPointInNew])
                                    ax.scatter(x, y, z, c=[RETRACT_COLOR], s=(retracted * SZ_FACTOR))

                # Subtractions do not appear in tree, so find by looking at last tree
                for branchIdx, branchId in enumerate(self.branchIDList):
                    if not self.subtracted[treeIdx - 1][branchIdx]:
                        continue
                    branchInLast = self.treeModels[treeIdx - 1].getBranchByID(branchId)
                    if branchInLast is None:
                        continue
                    # Draw at the parent of the subtracted branch, not the end point.
                    drawAt = branchInLast.parentPoint
                    if drawAt is not None:
                        # Walk up the old tree until a point exists in the new
                        # tree to connect the removal to.
                        drawAtInNew = treeModel.getPointByID(drawAt.id)
                        while drawAtInNew is None and drawAt is not None:
                            drawAt = drawAt.nextPointInBranch(delta=-1)
                            if drawAt is not None:
                                drawAtInNew = treeModel.getPointByID(drawAt.id)
                        if drawAt is None or drawAtInNew is None:
                            continue

                        sz = self.filoLengths[treeIdx-1][branchIdx] * SZ_FACTOR
                        if self.dendrogram:
                            x = [denX[drawAtInNew.id]]
                            y = [denY[drawAtInNew.id]]
                            ax.scatter(x, y, c=[GONE_COLOR], s=sz)
                        else:
                            x, y, z = treeModel.worldCoordPoints([drawAtInNew])
                            ax.scatter(x, y, z, c=[GONE_COLOR], s=sz)

                # For debugging puposes, maybe remove?
                print ("Stack #%d -> #%d" % (treeIdx, treeIdx + 1))
                print ("  - #Added        = %d" % np.sum(self.added[treeIdx-1]))
                print ("  - #Subtracted   = %d" % np.sum(self.subtracted[treeIdx-1]))
                print ("  - #Transitioned = %d" % np.sum(self.transitioned[treeIdx-1]))
                print ("  - #Extensions   = %d" % growCount)
                print ("  - #Retractions  = %d" % shrinkCount)

            # And finally draw the soma as a big sphere (if present):
            if treeModel.rootPoint is not None:
                if not self.dendrogram:
                    x, y, z = treeModel.worldCoordPoints([treeModel.rootPoint])
                    ax.scatter(x, y, z, c=[TREE_COLOUR], s=350)

            # Make equal aspect ratio:
            if not self.dendrogram:
                x, y, z = treeModel.worldCoordPoints(treeModel.flattenPoints())
                xmin, xmax = np.min(x), np.max(x)
                ymin, ymax = np.min(y), np.max(y)
                zmin, zmax = np.min(z), np.max(z)
                r = (0.5 * max(xmax - xmin, ymax - ymin, zmax - zmin)) * 1.1
                xM, yM, zM = (xmax + xmin) / 2, (ymax + ymin) / 2, (zmax + zmin) / 2
                ax.set_xlim3d(xM - r, xM + r)
                ax.set_ylim3d(yM - r, yM + r)
                ax.set_zlim3d(zM - r, zM + r)
            else:
                xM, yM = (xmaxD + xminD) / 2, (ymaxD + yminD) / 2
                xR, yR = (0.5 * (xmaxD - xminD) * 1.1), (0.5 * (ymaxD - yminD) * 1.1)
                ax.set_xlim(xM - xR, xM + xR)
                ax.set_ylim(yM - yR, yM + yR)

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
                if self.dendrogram:
                    # No movement, so skip?
                    pass
                else:
                    ax.view_init(elev=eAx.elev, azim=eAx.azim)
                    ax.set_xlim3d(event.inaxes.get_xlim3d(), emit=False)
                    ax.set_ylim3d(event.inaxes.get_ylim3d(), emit=False)
                    ax.set_zlim3d(event.inaxes.get_zlim3d(), emit=False)

    def canPrev(self):
        return self.firstTree > 0

    def canNext(self):
        return self.firstTree < len(self.treeModels) - MAX_TREE_COUNT

    def previous(self, toEnd):
        endIdx = 0
        nextIdx = endIdx if toEnd else max(self.firstTree - 1, endIdx)
        if nextIdx != self.firstTree:
            self.firstTree = nextIdx
            self.needToUpdate()

    def next(self, toEnd):
        endIdx = len(self.treeModels) - MAX_TREE_COUNT
        nextIdx = endIdx if toEnd else min(self.firstTree + 1, endIdx)
        if nextIdx != self.firstTree:
            self.firstTree = nextIdx
            self.needToUpdate()

    def set3D(self, is3D):
        if self.dendrogram != is3D:
            # No change, skip:
            return
        self.dendrogram = not is3D
        super(Motility3DCanvas, self).set3D(is3D)
        self.needToUpdate()
