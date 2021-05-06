from PyQt5 import QtCore, QtWidgets
from .overlayCanvas import OverlayCanvas

# Scrollable list of stacks, showing registration between stack pairs.
class OverlayViewWindow(QtWidgets.QMainWindow):
    def __init__(self, parent, fullState, windowIndex):
        super(OverlayViewWindow, self).__init__(parent)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowTitle('Overlay Image: Timepoints {} -> {}'.format((windowIndex-1), windowIndex))


        self.view = OverlayCanvas(self, fullState, windowIndex)

        root = QtWidgets.QWidget(self)
        l = QtWidgets.QHBoxLayout(root)
        l.setContentsMargins(0, 0, 0, 0)
        l.addWidget(self.view)
        root.setFocus()
        self.setCentralWidget(root)
