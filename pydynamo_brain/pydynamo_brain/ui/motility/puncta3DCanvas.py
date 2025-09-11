import numpy as np

from pydynamo_brain.analysis import addedSubtractedTransitioned, motility
from pydynamo_brain.ui.baseMatplotlibCanvas import BaseMatplotlibCanvas
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
class Puncta3DCanvas(BaseMatplotlibCanvas):
    def __init__(self, parent, selectedTree, treeModels, fullstate, filePaths, opt, sizeFactor=10, *args, **kwargs):
        self.firstTree = max(0, min(selectedTree - 1, len(treeModels) - MAX_TREE_COUNT))
        self.treeModels = treeModels
        self.puncta = fullstate.puncta
        self.puncta = [list(tp) for tp in self.puncta]
        self.filePaths = filePaths
        self.options = opt
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

        nPlots = min(len(treeModels), MAX_TREE_COUNT)
        super(Puncta3DCanvas, self).__init__(*args, in3D=True, subplots=nPlots, **kwargs)
        self.fig.canvas.mpl_connect('motion_notify_event', self.handleMove)
        self.fig.subplots_adjust(top=0.95, bottom=0.05, right=0.95, left=0.05, wspace=0.05, hspace=0.05)
        print("Puncta data for:", len(self.puncta))

    def compute_initial_figure(self):
        SZ_FACTOR = self.sizeFactor

        xminD, xmaxD, yminD, ymaxD = 0, 0, 0, 0

        # Update colors to be white on black:),subplots=nPlots, *
        print ("")
        for offset, ax in enumerate(self.axes):
            treeIdx = self.firstTree + offset
            treeModel = self.treeModels[treeIdx]
            ax.set_title(util.createTitle(treeIdx, self.filePaths[treeIdx]))
            ax.set_facecolor("white")
     
            ax.xaxis.set_pane_color((1.0,1.0,1.0,1.0))
            ax.yaxis.set_pane_color((1.0,1.0,1.0,1.0))
            ax.zaxis.set_pane_color((1.0,1.0,1.0,1.0))
            ax.xaxis._axinfo['grid'].update({'linewidth':0.25,'color':'gray'})
            ax.yaxis._axinfo['grid'].update({'linewidth':0.25,'color':'gray'})
            ax.zaxis._axinfo['grid'].update({'linewidth':0.25,'color':'gray'})

            # Draw lines for each branch:
            for branch in treeModel.branches:
                if branch.parentPoint is None:
                    continue
                points = [branch.parentPoint] + branch.points
    
                x, y, z = treeModel.worldCoordPoints(points)
                ax.plot(x, y, z, c=TREE_COLOUR) # TODO - draw axon differently?
            
            # Draw filo for each branch:
            if treeIdx > 0:

                added_count = int(0)
                subtracted_count = int(0)
                grew_count = int(0)
                shrunk_count = int(0)

                oldPuncta = self.puncta[treeIdx - 1]
                oldpunctaID = {puncta.id for puncta in oldPuncta}

                # current time point
                newPuncta = self.puncta[treeIdx]
                newpunctaID = {puncta.id for puncta in newPuncta}

                # compute changes
                added   = newpunctaID - oldpunctaID   # in new but not in old
                removed = oldpunctaID - newpunctaID   # in old but not in new
                oldpunctaID = [puncta.id for puncta in oldPuncta]
                newpunctaID = [puncta.id for puncta in newPuncta]

                growCount, shrinkCount = 0, 0
                for punctaPoint in oldPuncta:
                    plot = True
                    if punctaPoint.id in removed:
                        color, sz = GONE_COLOR, punctaPoint.radius * SZ_FACTOR
                        plot = True # Don't draw transitions ?!

                        if plot:
                    
                            x, y, z = treeModel.worldCoordPoints([punctaPoint])
                            ax.scatter(x, y, z, c=[color], s=sz)
                            subtracted_count += 1

                for punctaPoint in newPuncta:

                    plot = True
                    if punctaPoint.id in added:
                        color, sz = ADDED_COLOR, punctaPoint.radius * SZ_FACTOR
                        added_count += 1

                    elif punctaPoint.id in removed:
                        color, sz = RETRACT_COLOR, punctaPoint.radius * SZ_FACTOR
                        plot = True # Don't draw transitions ?!
                    else:
                        _idx = oldpunctaID.index(punctaPoint.id)
                        mot = punctaPoint.radius - oldPuncta[_idx].radius

                        if abs(mot) >= self.options.minMotilityDist:
                            color = GROW_COLOR if mot > 0 else SHRINK_COLOR
                            if color == GROW_COLOR:
                                 grew_count += 1
                            else:
                                shrunk_count += 1
                            sz = punctaPoint.radius * SZ_FACTOR
                        else:
                            color = GREY_COLOUR
                            sz = punctaPoint.radius * SZ_FACTOR

                    if plot:
                 
                        x, y, z = treeModel.worldCoordPoints([punctaPoint])
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
          
                                x, y, z = oldTreeModel.worldCoordPoints([childPoint])
                                childPointInNew = treeModel.getPointByID(childPoint.id)
                                if childPointInNew is not None:
                                    x, y, z = treeModel.worldCoordPoints([childPointInNew])
                                ax.scatter(x, y, z, c=[RETRACT_COLOR], s=(retracted * SZ_FACTOR))

            
            
            
                # For debugging puposes, maybe remove?
                print ("Stack #%d -> #%d" % (treeIdx, treeIdx + 1))
                print ("  - #Added        = %d" % added_count)
                print ("  - #Subtracted   = %d" % subtracted_count)
                print ("  - #Grew   = %d" % grew_count)
                print ("  - #Shrunk  = %d" % shrunk_count)


            # And finally draw the soma as a big sphere (if present):
            if treeModel.rootPoint is not None:
                x, y, z = treeModel.worldCoordPoints([treeModel.rootPoint])
                ax.scatter(x, y, z, c=[TREE_COLOUR], s=350)

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
        super(Puncta3DCanvas, self).set3D(is3D)
        self.needToUpdate()
