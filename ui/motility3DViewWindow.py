import math
import numpy as np

from PyQt5 import QtCore, QtWidgets

from .common import cursorPointer
from .motility3DCanvas import Motility3DCanvas, MAX_TREE_COUNT

class Motility3DViewWindow(QtWidgets.QMainWindow):
    def __init__(self, parent, middleIdx, treeModels, filePaths, opt):
        QtWidgets.QMainWindow.__init__(self, parent)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowTitle('Motility')

        root = QtWidgets.QWidget(self)
        self.view3D = Motility3DCanvas(parent, middleIdx, treeModels, filePaths, opt)
        self.nTrees = len(treeModels)

        self.buttonL = QtWidgets.QPushButton("◀ Previous", self)
        self.buttonL.setToolTip("Previous diagram")
        self.buttonL.clicked.connect(self.previous)
        cursorPointer(self.buttonL)
        self.buttonR = QtWidgets.QPushButton("Next ▶", self)
        self.buttonR.setToolTip("Next diagram")
        self.buttonR.clicked.connect(self.next)
        cursorPointer(self.buttonR)

        # Assemble the view hierarchy.
        l = QtWidgets.QHBoxLayout(root)
        l.setContentsMargins(0, 0, 0, 0)
        l.addWidget(self.buttonL)
        l.addWidget(self.view3D)
        l.addWidget(self.buttonR)
        root.setFocus()
        self.setCentralWidget(root)
        screenWidth = QtWidgets.QDesktopWidget().availableGeometry().width()
        scaleFactor = 1.0 # Compensate for title/padding to plots
        treesShown = min(len(treeModels), MAX_TREE_COUNT)
        self.resize(screenWidth, screenWidth / treesShown * scaleFactor)
        self.updateButtons()

    def keyPressEvent(self, event):
        ctrlPressed = (event.modifiers() & QtCore.Qt.ControlModifier)
        key = event.key()
        if key == QtCore.Qt.Key_Left:
            self.previous(ctrlPressed)
        elif key == QtCore.Qt.Key_Right:
            self.next(ctrlPressed)

    def previous(self, toEnd=False):
        self.view3D.previous(toEnd)
        self.updateButtons()
        self.setFocus(True)

    def next(self, toEnd=False):
        self.view3D.next(toEnd)
        self.updateButtons()
        self.setFocus(True)

    def updateButtons(self):
        canPrev = self.view3D.firstTree > 0
        canNext = self.view3D.firstTree < self.nTrees - MAX_TREE_COUNT
        self.buttonL.setEnabled(canPrev)
        self.buttonR.setEnabled(canNext)
