import math
import numpy as np

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.Qt import Qt

from model import MotilityOptions, ProjectOptions

from .common import cursorPointer, floatOrDefault

class AnalysisWindow(QtWidgets.QMainWindow):
    def __init__(self, parent):
        QtWidgets.QMainWindow.__init__(self, parent)
        self.root = QtWidgets.QWidget(self)
        self.layout = QtWidgets.QVBoxLayout(self.root)

        # Per-tree
        self.tabTree = QtWidgets.QWidget(self.root)
        self.layTree = QtWidgets.QHBoxLayout(self.tabTree)

        self.listTree = QtWidgets.QListWidget(self.tabTree)
        self._addItem(self.listTree, 0, 'Point Count')
        self._addItem(self.listTree, 1, 'Branch Count')
        self._addItem(self.listTree, 2, 'TDBL')
        self.listTree.currentItemChanged.connect(self.treeItemClicked)

        self.optTree = QtWidgets.QFrame()
        self.optTree.setFrameStyle(QtWidgets.QFrame.Box | QtWidgets.QFrame.Raised)
        self.optTree.setLineWidth(2)
        self.optTree.setFixedSize(400, 500)
        self.layTree.addWidget(self.listTree)
        self.layTree.addWidget(self.optTree)

        # Per-branch
        self.tabBranch = QtWidgets.QWidget(self.root)
        self.layBranch = QtWidgets.QHBoxLayout(self.tabBranch)

        self.listBranch = QtWidgets.QListWidget(self.tabBranch)
        self._addItem(self.listBranch, 0, 'Length')
        self._addItem(self.listBranch, 1, 'Type')
        self._addItem(self.listBranch, 2, 'Parent IDs')
        self.listBranch.currentItemChanged.connect(self.branchItemClicked)

        self.optBranch = QtWidgets.QFrame()
        self.optBranch.setFrameStyle(QtWidgets.QFrame.Box | QtWidgets.QFrame.Raised)
        self.optBranch.setLineWidth(2)
        self.optBranch.setFixedSize(400, 500)
        self.layBranch.addWidget(self.listBranch)
        self.layBranch.addWidget(self.optBranch)

        # Per-puncta
        self.tabPuncta = QtWidgets.QWidget(self.root)
        self.layPuncta = QtWidgets.QHBoxLayout(self.tabPuncta)

        self.listPuncta = QtWidgets.QListWidget(self.tabPuncta)
        self._addItem(self.listPuncta, 0, 'Size')
        self._addItem(self.listPuncta, 1, 'Intensity')
        self.listPuncta.currentItemChanged.connect(self.punctaItemClicked)

        self.optPuncta = QtWidgets.QFrame()
        self.optPuncta.setFrameStyle(QtWidgets.QFrame.Box | QtWidgets.QFrame.Raised)
        self.optPuncta.setLineWidth(2)
        self.optPuncta.setFixedSize(400, 500)
        self.layPuncta.addWidget(self.listPuncta)
        self.layPuncta.addWidget(self.optPuncta)

        self.tabs = QtWidgets.QTabWidget()
        self.tabs.addTab(self.tabTree, "Tree analysis")
        self.tabs.addTab(self.tabBranch, "Branch analysis")
        self.tabs.addTab(self.tabPuncta, "Puncta analysis")
        self.layout.addWidget(self.tabs)

        # Button to actually run the analysis
        bRun = cursorPointer(QtWidgets.QPushButton("Run analysis", self))
        bRun.clicked.connect(self.runAnalysis)
        bRun.setMaximumWidth(200)
        self.layout.addWidget(bRun, 0, QtCore.Qt.AlignRight)

        self.root.setFocus()
        self.setCentralWidget(self.root)

        combined = QtCore.QSize()
        combined.setWidth(800)
        combined.setHeight(600)
        self.resize(combined)

        self.setWindowTitle("Analysis")
        self._centerWindow()

    def _addItem(self, listWidget, idx, text):
        # Build the widget itself.
        container = QtWidgets.QWidget()
        wText = cursorPointer(QtWidgets.QLabel(text))
        wText.setMinimumSize(300, 1)
        #bViz = QtWidgets.QPushButton("Show" if stackHidden else "Hide")
        #bDel = QtWidgets.QPushButton("Delete")
        l = QtWidgets.QHBoxLayout()
        l.addWidget(wText)
        #l.addWidget(bViz)
        #l.addWidget(bDel)
        l.addStretch()
        l.setSizeConstraint(QtWidgets.QLayout.SetFixedSize)
        container.setLayout(l)

        # Build the list item, and add the widget:
        itemN = QtWidgets.QListWidgetItem()
        itemN.setSizeHint(container.sizeHint())
        listWidget.addItem(itemN)
        listWidget.setItemWidget(itemN, container)

        itemData = {'text': text, 'idx': idx}
        itemN.setData(Qt.UserRole, itemData)

    # TODO - share with others who use the same.
    def _centerWindow(self):
        frameGm = self.frameGeometry()
        centerPoint = QtWidgets.QDesktopWidget().availableGeometry().center()
        frameGm.moveCenter(centerPoint)
        self.move(frameGm.topLeft())

    def treeItemClicked(self, item):
        text = "%s :: Options for %s" % ('Tree', item.data(Qt.UserRole)['text'])
        print ("TODO: " + text)

    def branchItemClicked(self, item):
        text = "%s :: Options for %s" % ('Branch', item.data(Qt.UserRole)['text'])
        print ("TODO: " + text)

    def punctaItemClicked(self, item):
        text = "%s :: Options for %s" % ('Puncta', item.data(Qt.UserRole)['text'])
        print ("TODO: " + text)

    def runAnalysis(self):
        print ("TODO: Actually run analysis...")
