from .baseMatplotlibCanvas import BaseMatplotlibCanvas

class Scatter3DCanvas(BaseMatplotlibCanvas):
    def __init__(self, hackModel, *args, **kwargs):
        self.hackModel = hackModel
        super(Scatter3DCanvas, self).__init__(*args, in3D=True, **kwargs)

    def compute_initial_figure(self):
        for branch in self.hackModel.branches:
            x = [p[0] for p in branch.points]
            y = [p[1] for p in branch.points]
            z = [p[2] for p in branch.points]
        self.axes.scatter(x, y, z)

    def needToUpdate(self):
        self.axes.cla()
        self.compute_initial_figure()
        self.draw()

    def mousePressEvent(self, event):
        print ("Clicked: (%d %d)" % (event.globalX(), event.globalY()))
        super(Scatter3DCanvas, self).mousePressEvent(event)
