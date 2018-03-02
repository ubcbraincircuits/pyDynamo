from PyQt5 import QtWidgets

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class BaseMatplotlibCanvas(FigureCanvas):
    # Ultimately, this is a QWidget (as well as a FigureCanvasAgg, etc.).
    def __init__(self, parent=None, width=5, height=4, dpi=100, in3D=False):
        fig = Figure(figsize=(width, height), dpi=dpi)
        fig.subplots_adjust(top=1.0, bottom=0.0, right=1.0, left=0.0)
        if in3D:
            self.axes = fig.add_subplot(111, projection='3d')
        else:
            self.axes = fig.add_subplot(111)
        self.compute_initial_figure()
        super(BaseMatplotlibCanvas, self).__init__(fig)
        if in3D:
            self.axes.mouse_init()
        self.setParent(parent)
        self.setStyleSheet("background-color:black;")
        FigureCanvas.setSizePolicy(self,
                                   QtWidgets.QSizePolicy.Expanding,
                                   QtWidgets.QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)

    def compute_initial_figure(self):
        pass
