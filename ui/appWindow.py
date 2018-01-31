import math
import numpy as np

from PyQt5 import QtCore, QtWidgets

import files

from .scatter3DCanvas import Scatter3DCanvas
from .dendriteCanvasActions import DendriteCanvasActions
from .dendriteVolumeCanvas import DendriteVolumeCanvas
from .np2qt import np2qt
from .QtImageViewer import QtImageViewer

class AppWindow(QtWidgets.QMainWindow):
    def __init__(self, imagePath, treeModel, uiState, parent=None):
        QtWidgets.QMainWindow.__init__(self, parent)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowTitle("Dynamo")
        self.statusBar().showMessage("Dynamo", 2000)

        # TODO - option for when imagePath=None, have a button to load an image?
        assert imagePath is not None
        imageVolume = files.tiffRead(imagePath)

        self.root = QtWidgets.QWidget(self)
        self.scatter3d = Scatter3DCanvas(treeModel, self.root, width=5, height=4, dpi=100)
        self.dendrites = DendriteVolumeCanvas(imageVolume, treeModel, uiState, self.scatter3d, self.root)
        self.actionHandler = DendriteCanvasActions(self.dendrites, treeModel, uiState)

        # Assemble the view hierarchy.
        l = QtWidgets.QHBoxLayout(self.root)
        l.addWidget(self.scatter3d)
        l.addWidget(self.dendrites)
        self.root.setFocus()
        self.setCentralWidget(self.root)

        # Top level menu:
        self.file_menu = QtWidgets.QMenu('&File', self)
        self.file_menu.addAction('&Quit', self.fileQuit, QtCore.Qt.CTRL + QtCore.Qt.Key_Q)
        self.menuBar().addMenu(self.file_menu)
        self.help_menu = QtWidgets.QMenu('&Help', self)
        self.menuBar().addSeparator()
        self.menuBar().addMenu(self.help_menu)
        self.help_menu.addAction('&Shortcuts', self.actionHandler.showHotkeys, QtCore.Qt.Key_F1)

    def fileQuit(self):
        self.close()

    def closeEvent(self, ce):
        self.fileQuit()

    def showHotkeys(self):
        self.actionHandler.showHotkeys()

    def keyPressEvent(self, event):
        # TODO: add menu items for some of these too.
        key = event.key()
        print (key)
        if   (key == ord(' ')):
            newP = np.random.rand(n, 3)
            newPRot = absorient.hackRotate(newP)
        elif (key == ord('1')):
            self.dendrites.changeZAxis(1)
        elif (key == ord('2')):
            self.dendrites.changeZAxis(-1)
        elif (key == ord('4')):
            self.actionHandler.changeBrightness(-1, 0)
        elif (key == ord('5')):
            self.actionHandler.changeBrightness(1, 0)
        elif (key == ord('6')):
            self.actionHandler.changeBrightness(0, 0, reset=True)
        elif (key == ord('7')):
            self.actionHandler.changeBrightness(0, -1)
        elif (key == ord('8')):
            self.actionHandler.changeBrightness(0, 1)
        elif (key == ord('X')):
            self.actionHandler.zoom(-0.2) # ~= ln(0.8) as used in matlab
        elif (key == ord('Z')):
            self.actionHandler.zoom(0.2)
        elif (key == ord('W')):
            self.actionHandler.pan(0, -1)
        elif (key == ord('A')):
            self.actionHandler.pan(-1, 0)
        elif (key == ord('S')):
            # TODO - ctrl-s = save
            self.actionHandler.pan(0, 1)
        elif (key == ord('D')):
            self.actionHandler.pan(1, 0)
        elif (key == ord('H')):
            self.dendrites.uiState.toggleLineWidth()
            self.dendrites.redraw()
        elif (key == ord('F')):
            self.dendrites.uiState.showAnnotations = not self.dendrites.uiState.showAnnotations
            self.dendrites.redraw()
        elif (key == ord('V')):
            self.dendrites.uiState.drawAllBranches = not self.dendrites.uiState.drawAllBranches
            self.dendrites.redraw()
        elif (key == ord('Q')):
            self.actionHandler.getAnnotation(self)
        elif (key == QtCore.Qt.Key_Delete):
            self.actionHandler.deleteCurrentPoint();
