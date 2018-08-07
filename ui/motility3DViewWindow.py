import math
import numpy as np

from PyQt5 import QtCore, QtWidgets

from .motility3DCanvas import Motility3DCanvas

class Motility3DViewWindow(QtWidgets.QMainWindow):
    def __init__(self, parent, treeModels, opt):
        QtWidgets.QMainWindow.__init__(self, parent)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowTitle('Motility')

        root = QtWidgets.QWidget(self)
        view3D = Motility3DCanvas(parent, treeModels, opt)

        # Assemble the view hierarchy.
        l = QtWidgets.QVBoxLayout(root)
        l.setContentsMargins(0, 0, 0, 0)
        l.addWidget(view3D)
        root.setFocus()
        self.setCentralWidget(root)
        screenWidth = QtWidgets.QDesktopWidget().availableGeometry().width()
        self.resize(screenWidth, screenWidth / len(treeModels))
