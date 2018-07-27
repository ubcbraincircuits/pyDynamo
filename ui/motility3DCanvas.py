from analysis import addedSubtractedTransitioned, motility

from .baseMatplotlibCanvas import BaseMatplotlibCanvas
from .dendritePainter import colorForBranch

MIN_MOTILITY = 0.1
GREY_COLOUR =  (0.75, 0.75, 0.75, 1.0)
ADDED_COLOR =  (0.00, 1.00, 0.00, 0.75)
TRANS_COLOR =  (0.00, 0.00, 0.00, 0.0) # Not shown ?! TODO: verify
GROW_COLOR =   (0.00, 1.00, 1.00, 0.75)
SHRINK_COLOR = (1.00, 0.00, 1.00, 0.75)
GONE_COLOR   = (1.00, 0.00, 0.00, 0.75)

# Draws a dendritic tree in 3D space that can be rotated by the user.
class Motility3DCanvas(BaseMatplotlibCanvas):
    def __init__(self, treeModels, sizeFactor=10, *args, **kwargs):
        self.treeModels = treeModels
        _, self.added, self.subtracted, self.transitioned, _, _ = addedSubtractedTransitioned(
            self.treeModels, excludeBasal=False, terminalDist=5, filoDist=5
        )
        mot, self.filoLengths = motility(
            self.treeModels, excludeBasal=False, includeAS=False, terminalDist=5, filoDist=5)
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
                for branchIdx, branch in enumerate(treeModel.branches):
                    plot = True
                    if self.added[treeIdx-1][branchIdx]:
                        color, sz = ADDED_COLOR, self.filoLengths[treeIdx][branchIdx] * SZ_FACTOR
                    elif self.transitioned[treeIdx-1][branchIdx]:
                        color, sz = TRANS_COLOR, self.filoLengths[treeIdx][branchIdx] * SZ_FACTOR
                        plot = False # Don't draw transitions ?!
                    else:
                        mot = self.motility[treeIdx-1][branchIdx]
                        if abs(mot) > MIN_MOTILITY:
                            color = GROW_COLOR if mot > 0 else SHRINK_COLOR
                            sz = abs(mot) * SZ_FACTOR
                        else:
                            plot = False
                    if plot:
                        if len(branch.points) != 0 :
                            x, y, z = treeModel.worldCoordPoints([branch.points[-1]])
                            ax.scatter(x, y, z, c=color, s=sz)

                    # Show removed branches from last point:
                    lastHasBranch = branchIdx < len(self.treeModels[treeIdx - 1].branches)
                    if lastHasBranch and self.treeModels[treeIdx - 1].branches[branchIdx] is not None:
                        for childPoint in self.treeModels[treeIdx - 1].branches[branchIdx].points:
                            retracted = 0
                            for childBranch in childPoint.children:
                                if not (childBranch is None or len(childBranch.points) == 0):
                                    retracted += self.filoLengths[treeIdx - 1][childBranch.indexInParent()]
                            if retracted > 0:
                                x, y, z = treeModel.worldCoordPoints([childPoint])
                                ax.scatter(x, y, z, c=GONE_COLOR, s=(retracted * SZ_FACTOR))
                        if self.subtracted[treeIdx - 1][branchIdx]:
                            drawAt = self.treeModels[treeIdx - 1].branches[branchIdx].points[-1] # End or parent?
                            if drawAt is not None:
                                sz = self.filoLengths[treeIdx-1][branchIdx] * SZ_FACTOR
                                x, y, z = treeModel.worldCoordPoints([drawAt])
                                ax.scatter(x, y, z, c=GONE_COLOR, s=sz)


            # And finally draw the soma as a big sphere (if present):
            if treeModel.rootPoint is not None:
                x, y, z = treeModel.worldCoordPoints([treeModel.rootPoint])
                ax.scatter(x, y, z, c=GREY_COLOUR, s=350)

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
