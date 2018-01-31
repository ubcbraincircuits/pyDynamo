import math
import numpy as np

from PyQt5 import QtCore, QtWidgets

from .appWindow import AppWindow

import files
from model import Tree, UIState

class InitialMenu(QtWidgets.QMainWindow):
    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowTitle("Dynamo")
        self.statusBar().showMessage("Dynamo", 2000)
        self.centerWindow()

        # Options #1 - Start New
        buttonN = QtWidgets.QPushButton("&New from Stack(s)", self)
        buttonN.setToolTip("Start new labelling from one or more images")
        buttonN.clicked.connect(self.newFromStacks)

        # Option #2 - Load existing
        buttonL = QtWidgets.QPushButton("&Open from File", self)
        buttonL.setToolTip("Open a previous session")
        buttonL.clicked.connect(self.openFromFile)

        # Assemble the view hierarchy.
        self.root = QtWidgets.QWidget(self)
        l = QtWidgets.QVBoxLayout(self.root)
        l.addWidget(buttonN, 0, QtCore.Qt.AlignHCenter)
        l.addWidget(buttonL, 0, QtCore.Qt.AlignHCenter | QtCore.Qt.AlignTop)
        self.root.setFocus()
        self.setCentralWidget(self.root)

        # Top level menu:
        self.fileMenu = QtWidgets.QMenu('&File', self)
        self.fileMenu.addAction('&New', self.newFromStacks, QtCore.Qt.CTRL + QtCore.Qt.Key_N)
        self.fileMenu.addAction('&Load', self.openFromFile, QtCore.Qt.CTRL + QtCore.Qt.Key_O)
        self.menuBar().addMenu(self.fileMenu)

    def centerWindow(self):
        self.resize(640, 480)
        frameGm = self.frameGeometry()
        centerPoint = QtWidgets.QDesktopWidget().availableGeometry().center()
        frameGm.moveCenter(centerPoint)
        self.move(frameGm.topLeft())

    def fileQuit(self):
        self.close()

    def closeEvent(self, ce):
        self.fileQuit()

    def newFromStacks(self):
        imageVolume = files.tiffRead('data/Live4-1-2015_09-16-03.tif')
        treeModel = Tree()
        uiState = UIState(tree=treeModel)
        uiApp = AppWindow(imageVolume, treeModel, uiState, parent=self)
        uiApp.show()
        self.hide()

    def openFromFile(self):
        QtWidgets.QMessageBox.warning(
            self,
            "Coming soon...",
            "To be added after file save/load working"
        )
