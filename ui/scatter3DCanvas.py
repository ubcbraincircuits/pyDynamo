from .baseMatplotlibCanvas import BaseMatplotlibCanvas

class Scatter3DCanvas(BaseMatplotlibCanvas):
    def __init__(self, data, *args, **kwargs):
        self.data = data
        super(Scatter3DCanvas, self).__init__(*args, in3D=True, **kwargs)

    def compute_initial_figure(self):
        self.axes.scatter(self.data[:, 0], self.data[:, 1], self.data[:, 2])

    def updateData(self, data):
        self.data = data
        self.axes.cla()
        self.axes.scatter(data[:, 0], data[:, 1], data[:, 2])
        self.draw()

    def mousePressEvent(self, event):
        print ("Clicked: (%d %d)" % (event.globalX(), event.globalY()))
        super(Scatter3DCanvas, self).mousePressEvent(event)
