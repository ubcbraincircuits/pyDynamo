import math
import numpy as np

from PyQt5 import QtCore, QtWidgets

from .dendrite3DCanvas import Dendrite3DCanvas

class Dendrite3DViewWindow(QtWidgets.QMainWindow):
    def __init__(self, parent, imagePath, treeModel):
        QtWidgets.QMainWindow.__init__(self, parent)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowTitle('3D Dendrite view for ' + imagePath)

        root = QtWidgets.QWidget(self)
        view3D = Dendrite3DCanvas(treeModel)

        # Assemble the view hierarchy.
        l = QtWidgets.QVBoxLayout(root)
        l.setContentsMargins(0, 0, 0, 0)
        l.addWidget(view3D)
        root.setFocus()
        self.setCentralWidget(root)
        self.resize(1024, 768)
