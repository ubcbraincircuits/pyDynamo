import math
import numpy as np

from PyQt5 import QtCore, QtWidgets
from PyQt5.Qt import Qt

class InitialMenu(QtWidgets.QMainWindow):
    def __init__(self, parent):
        QtWidgets.QMainWindow.__init__(self, parent)

        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowTitle("Dynamo")
        self.statusBar().showMessage("Dynamo", 2000)
        self.centerWindow()

        # Options #1 - Start New
        buttonN = QtWidgets.QPushButton("&New from Stack(s)", self)
        buttonN.setToolTip("Start new labelling from one or more images")
        buttonN.clicked.connect(parent.newFromStacks)

        # Option #2 - Load existing
        buttonL = QtWidgets.QPushButton("&Open from File", self)
        buttonL.setToolTip("Open a previous session")
        buttonL.clicked.connect(parent.openFromFile)

        # Option #2 - Import from matlab
        buttonI = QtWidgets.QPushButton("&Import from Matlab .mat", self)
        buttonI.setToolTip("Import from Matlab save file")
        buttonI.clicked.connect(parent.importFromMatlab)

        # Assemble the view hierarchy.
        self.root = QtWidgets.QWidget(self)
        l = QtWidgets.QVBoxLayout(self.root)
        l.addWidget(buttonN, 0, QtCore.Qt.AlignHCenter)
        l.addWidget(buttonL, 0, QtCore.Qt.AlignHCenter)
        l.addWidget(buttonI, 0, QtCore.Qt.AlignHCenter)
        self.root.setFocus()
        self.setCentralWidget(self.root)

        # Top level menu:
        self.fileMenu = QtWidgets.QMenu('&File', self)
        self.fileMenu.addAction('&New', parent.newFromStacks, QtCore.Qt.CTRL + QtCore.Qt.Key_N)
        self.fileMenu.addAction('&Open', parent.openFromFile, QtCore.Qt.CTRL + QtCore.Qt.Key_O)
        self.fileMenu.addAction('&Import', parent.importFromMatlab, QtCore.Qt.CTRL + QtCore.Qt.Key_I)
        self.menuBar().addMenu(self.fileMenu)

    def centerWindow(self):
        self.resize(640, 480)
        frameGm = self.frameGeometry()
        centerPoint = QtWidgets.QDesktopWidget().availableGeometry().center()
        frameGm.moveCenter(centerPoint)
        self.move(frameGm.topLeft())

    def keyPressEvent(self, event):
        self.parent().keyPressEvent(event)
