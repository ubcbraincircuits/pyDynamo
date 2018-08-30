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

        # Set up menu
        fileMenu = QtWidgets.QMenu('File', self)
        fileMenu.addAction('Save images to .png...', self.saveImagesAsPng, QtCore.Qt.CTRL + QtCore.Qt.Key_S)
        self.menuBar().addMenu(fileMenu)
        
        viewMenu = QtWidgets.QMenu('View', self)
        viewMenu.addAction('Show 3D', self.show3D, QtCore.Qt.Key_3)
        viewMenu.addAction('Show 2D Dendrograms', self.show2D, QtCore.Qt.Key_2)
        viewMenu.addSeparator()
        viewMenu.addAction('First Stack', self.firstStack, QtCore.Qt.CTRL + QtCore.Qt.Key_Left)
        viewMenu.addAction('Previous Stack', self.previous, QtCore.Qt.Key_Left)
        viewMenu.addAction('Next Stack', self.next, QtCore.Qt.Key_Right)
        viewMenu.addAction('Last Stack', self.lastStack, QtCore.Qt.CTRL + QtCore.Qt.Key_Right)
        self.menuBar().addMenu(viewMenu)

    def saveImagesAsPng(self):
        self.view3D.saveAxesAsPng()

    def show3D(self):
        self.view3D.set3D(True)

    def show2D(self):
        self.view3D.set3D(False)

    def firstStack(self):
        self.previous(True)

    def lastStack(self):
        self.next(False)

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
