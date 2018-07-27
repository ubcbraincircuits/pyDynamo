from .baseMatplotlibCanvas import BaseMatplotlibCanvas
from .dendritePainter import colorForBranch

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
            ax.plot(x, y, z, c=colorForBranch(i))

        # And finally draw the soma as a big sphere:
        x, y, z = self.treeModel.worldCoordPoints([self.treeModel.rootPoint])
        ax.scatter(x, y, z, c=colorForBranch(0), s=100)

    def needToUpdate(self):
        self.axes[0].cla()
        self.compute_initial_figure()
        self.draw()

    # def mousePressEvent(self, event):
        # print ("Clicked: (%d %d)" % (event.globalX(), event.globalY()))
        # super(Scatter3DCanvas, self).mousePressEvent(event)
