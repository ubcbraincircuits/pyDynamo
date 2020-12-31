from PyQt5 import QtCore, QtWidgets

from .traceCanvas import TraceCanvas

# Plot view showing traces associated to all selected points.
class TraceViewWindow(QtWidgets.QMainWindow):
    def __init__(self, parent, fullState, windowIndex, pointID):
        super(TraceViewWindow, self).__init__(parent)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowTitle('Traces')

        self.view = TraceCanvas(self, fullState, windowIndex, pointID)

        root = QtWidgets.QWidget(self)
        l = QtWidgets.QHBoxLayout(root)
        l.setContentsMargins(0, 0, 0, 0)
        l.addWidget(self.view)
        root.setFocus()
        self.setCentralWidget(root)

        # TODO: Menu options for DF/F0, okada and smooth filters.
        #viewMenu = QtWidgets.QMenu('View', self)
        #viewMenu.addAction('Show 3D', self.show3D, QtCore.Qt.Key_3)
        #viewMenu.addAction('Show 2D Dendrograms', self.show2D, QtCore.Qt.Key_2)
        #viewMenu.addSeparator()
        #self._addScrollActions(viewMenu)
        #self.menuBar().addMenu(viewMenu)
