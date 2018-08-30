from PyQt5 import QtWidgets

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.transforms import Bbox

class BaseMatplotlibCanvas(FigureCanvas):
    # Ultimately, this is a QWidget (as well as a FigureCanvasAgg, etc.).
    def __init__(self, parent=None, width=5, height=4, dpi=100, in3D=False, subplots=1):
        fig = Figure(figsize=(width, height), dpi=dpi)
        fig.subplots_adjust(top=1.0, bottom=0.0, right=1.0, left=0.0, wspace=0.0, hspace=0.0)
        if in3D:
            self.axes = [fig.add_subplot(1, subplots, i + 1, projection='3d') for i in range(subplots)]
        else:
            self.axes = [fig.add_subplot(1, subplots, i + 1) for i in range(subplots)]
        self.compute_initial_figure()
        super(BaseMatplotlibCanvas, self).__init__(fig)
        if in3D:
            for ax in self.axes:
                ax.mouse_init()
                ax.view_init(elev=-90, azim=-90)
        self.setParent(parent)
        self.setStyleSheet("background-color:black;")
        FigureCanvas.setSizePolicy(self,
                                   QtWidgets.QSizePolicy.Expanding,
                                   QtWidgets.QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)
        self.fig = fig
        self.in3D = in3D

    def compute_initial_figure(self):
        pass

    def set3D(self, in3D):
        if self.in3D != in3D:
            self.in3D = in3D
            self.resetAxes()

    def resetAxes(self):
        subplots = len(self.axes)
        for ax in self.axes:
            self.fig.delaxes(ax)
        if self.in3D:
            self.axes = [self.fig.add_subplot(1, subplots, i + 1, projection='3d') for i in range(subplots)]
            for ax in self.axes:
                ax.mouse_init()
                ax.view_init(elev=-90, azim=-90)
        else:
            self.axes = [self.fig.add_subplot(1, subplots, i + 1) for i in range(subplots)]

    def saveAxesAsPng(self):
        filePath, _ = QtWidgets.QFileDialog.getSaveFileName(self,
            "PNG output file", "", "PNG files (*.png)"
        )
        if filePath is None or filePath == "":
            return
        if not filePath.endswith(".png"):
            filePath += ".png"
        for i, ax in enumerate(self.axes):
            axPath = filePath
            if len(self.axes) > 1:
                axPath = filePath.replace('.png', '_%d.png' % (i))
            self.fig.savefig(axPath, bbox_inches=self._axesExtent(ax))

    def _axesExtent(self, ax, pad=0.0):
        # For text objects, we need to draw the figure first
        ax.figure.canvas.draw()
        items = ax.get_xticklabels() + ax.get_yticklabels()
        # items += [ax, ax.title, ax.xaxis.label, ax.yaxis.label]
        items += [ax, ax.title]
        bbox = Bbox.union([item.get_window_extent() for item in items])
        bbox = bbox.expanded(1.0 + pad, 1.0 + pad)
        return bbox.transformed(self.fig.dpi_scale_trans.inverted())
