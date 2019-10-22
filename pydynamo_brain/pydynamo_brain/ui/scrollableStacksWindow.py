from PyQt5 import QtCore, QtWidgets

from .common import cursorPointer

DEFAULT_TREE_COUNT = 3 # Show this many trees, scroll to the others.

class ScrollableStacksWindow(QtWidgets.QMainWindow):
    """Window that shows a bunch of stacks and lets you scroll left & right."""
    def __init__(self, parent, treeModels, title, view, treesShown=DEFAULT_TREE_COUNT):
        super(ScrollableStacksWindow, self).__init__(parent)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowTitle(title)

        self.treeModels = treeModels
        self.nTrees = len(treeModels)

        self.view = view

        self.buttonL = QtWidgets.QPushButton("◀ Previous", self)
        self.buttonL.setToolTip("Previous diagram")
        self.buttonL.clicked.connect(self.previous)
        cursorPointer(self.buttonL)
        self.buttonR = QtWidgets.QPushButton("Next ▶", self)
        self.buttonR.setToolTip("Next diagram")
        self.buttonR.clicked.connect(self.next)
        cursorPointer(self.buttonR)

        # Assemble the view hierarchy.
        root = QtWidgets.QWidget(self)
        l = QtWidgets.QHBoxLayout(root)
        l.setContentsMargins(0, 0, 0, 0)
        l.addWidget(self.buttonL)
        l.addWidget(self.view)
        l.addWidget(self.buttonR)
        root.setFocus()
        self.setCentralWidget(root)
        screenWidth = QtWidgets.QDesktopWidget().availableGeometry().width()
        scaleFactor = 1.0 # Compensate for title/padding to plots
        treesShown = min(self.nTrees, treesShown)
        self.resize(screenWidth, screenWidth / treesShown * scaleFactor)
        self.updateButtons()

        # Set up menu
        fileMenu = QtWidgets.QMenu('File', self)
        fileMenu.addAction('Save images to .png...', self.saveImagesAsPng, QtCore.Qt.CTRL + QtCore.Qt.Key_S)
        self.menuBar().addMenu(fileMenu)

    def _addScrollActions(self, menu):
        menu.addAction('First Stack', self.firstStack, QtCore.Qt.CTRL + QtCore.Qt.Key_Left)
        menu.addAction('Previous Stack', self.previous, QtCore.Qt.Key_Left)
        menu.addAction('Next Stack', self.next, QtCore.Qt.Key_Right)
        menu.addAction('Last Stack', self.lastStack, QtCore.Qt.CTRL + QtCore.Qt.Key_Right)

    def saveImagesAsPng(self):
        self.view.saveAxesAsPng()

    def firstStack(self):
        self.previous(True)

    def lastStack(self):
        self.next(True)

    def previous(self, toEnd=False):
        if self.view.canPrev():
            self.view.previous(toEnd)
            self.updateButtons()
            self.setFocus(True)

    def next(self, toEnd=False):
        if self.view.canNext():
            self.view.next(toEnd)
            self.updateButtons()
            self.setFocus(True)

    def updateButtons(self):
        self.buttonL.setEnabled(self.view.canPrev())
        self.buttonR.setEnabled(self.view.canNext())
