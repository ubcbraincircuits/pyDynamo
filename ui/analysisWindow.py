import math
import numpy as np

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.Qt import Qt

from analysis import allTrees, allBranches, allPuncta
from analysis.ui import branchOptions, punctaOptions, treeOptions
from model import MotilityOptions, ProjectOptions

from .common import cursorPointer, floatOrDefault

class AnalysisWindow(QtWidgets.QMainWindow):
    def __init__(self, parent):
        QtWidgets.QMainWindow.__init__(self, parent)
        self.root = QtWidgets.QWidget(self)
        self.layout = QtWidgets.QVBoxLayout(self.root)

        self.analysisOptions = {}
        self.analysisMethods = self._buildMethods()
        for methodsPerType in self.analysisMethods.values():
            for method in methodsPerType:
                self.analysisOptions.update(method.defaultValues())
        print (self.analysisOptions)

        self.lastOption = None

        # TODO - clean up this section

        # Per-tree
        self.tabTree = QtWidgets.QWidget(self.root)
        self.layTree = QtWidgets.QHBoxLayout(self.tabTree)

        self.listTree = QtWidgets.QListWidget(self.tabTree)
        for treeMethod in self.analysisMethods['tree']:
            self._addItem(self.listTree, treeMethod)
        self.listTree.currentItemChanged.connect(self.treeItemClicked)

        self.optTree = QtWidgets.QFrame()
        self.optTreeLayout = QtWidgets.QVBoxLayout(self.optTree)
        self.optTree.setFrameStyle(QtWidgets.QFrame.Box | QtWidgets.QFrame.Raised)
        self.optTree.setLineWidth(2)
        self.optTree.setFixedSize(400, 500)
        self.layTree.addWidget(self.listTree)
        self.layTree.addWidget(self.optTree)

        # Per-branch
        self.tabBranch = QtWidgets.QWidget(self.root)
        self.layBranch = QtWidgets.QHBoxLayout(self.tabBranch)

        self.listBranch = QtWidgets.QListWidget(self.tabBranch)
        for branchMethod in self.analysisMethods['branch']:
            self._addItem(self.listBranch, branchMethod)
        self.listBranch.currentItemChanged.connect(self.branchItemClicked)

        self.optBranch = QtWidgets.QFrame()
        self.optBranchLayout = QtWidgets.QVBoxLayout(self.optBranch)
        self.optBranch.setFrameStyle(QtWidgets.QFrame.Box | QtWidgets.QFrame.Raised)
        self.optBranch.setLineWidth(2)
        self.optBranch.setFixedSize(400, 500)
        self.layBranch.addWidget(self.listBranch)
        self.layBranch.addWidget(self.optBranch)

        # Per-puncta
        self.tabPuncta = QtWidgets.QWidget(self.root)
        self.layPuncta = QtWidgets.QHBoxLayout(self.tabPuncta)

        self.listPuncta = QtWidgets.QListWidget(self.tabPuncta)
        for branchMethod in self.analysisMethods['puncta']:
            self._addItem(self.listPuncta, branchMethod)
        self.listPuncta.currentItemChanged.connect(self.punctaItemClicked)

        self.optPuncta = QtWidgets.QFrame()
        self.optPunctaLayout = QtWidgets.QVBoxLayout(self.optPuncta)
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

    def _addItem(self, listWidget, method):
        # Build the widget itself.
        container = QtWidgets.QWidget()
        wText = cursorPointer(QtWidgets.QLabel(method.name))
        wText.setMinimumSize(300, 1)
        l = QtWidgets.QHBoxLayout()
        l.addWidget(wText)
        l.addStretch()
        l.setSizeConstraint(QtWidgets.QLayout.SetFixedSize)
        container.setLayout(l)

        # Build the list item, and add the widget:
        itemN = QtWidgets.QListWidgetItem()
        itemN.setSizeHint(container.sizeHint())
        listWidget.addItem(itemN)
        listWidget.setItemWidget(itemN, container)

        itemN.setData(Qt.UserRole, method)

    # TODO - share with others who use the same.
    def _centerWindow(self):
        frameGm = self.frameGeometry()
        centerPoint = QtWidgets.QDesktopWidget().availableGeometry().center()
        frameGm.moveCenter(centerPoint)
        self.move(frameGm.topLeft())

    def treeItemClicked(self, item):
        if self.lastOption is not None:
            self.analysisOptions.update(self.lastOption.readOptions())

        method = item.data(Qt.UserRole)
        optLayout = self.optTreeLayout
        self._clearChildWidgets(optLayout)
        method.fillOptions(optLayout, self.analysisOptions)
        optLayout.addStretch(1)
        self.lastOption = method

    def branchItemClicked(self, item):
        if self.lastOption is not None:
            self.analysisOptions.update(self.lastOption.readOptions())

        method = item.data(Qt.UserRole)
        optLayout = self.optBranchLayout
        print ("Size: ", optLayout.count())
        self._clearChildWidgets(optLayout)
        method.fillOptions(optLayout, self.analysisOptions)
        optLayout.addStretch(1)
        self.lastOption = method

    def punctaItemClicked(self, item):
        if self.lastOption is not None:
            self.analysisOptions.update(self.lastOption.readOptions())

        method = item.data(Qt.UserRole)
        optLayout = self.optPunctaLayout
        print ("Size: ", optLayout.count())
        self._clearChildWidgets(optLayout)
        method.fillOptions(optLayout, self.analysisOptions)
        optLayout.addStretch(1)
        self.lastOption = method

    def runAnalysis(self):
        if self.lastOption is not None:
            self.analysisOptions.update(self.lastOption.readOptions())

        selected = self.tabs.currentIndex()
        methods, runner = [], None
        if selected == 0:
            methods = self.analysisMethods['tree']
            runner = allTrees
        elif selected == 1:
            methods = self.analysisMethods['branch']
            runner = allBranches
        else:
            methods = self.analysisMethods['puncta']
            runner = allPuncta

        selectedFunctions = []
        for method in methods:
            if method.shouldRun(self.analysisOptions):
                selectedFunctions.append(method.methodToCall)

        # Filter out internal (de)selection markers
        filteredOptions = {}
        for k, v in self.analysisOptions.items():
            if "_do " not in k:
                filteredOptions[k] = v

        fullState = self.parent().fullState
        result = runner(fullState, selectedFunctions, **filteredOptions)
        print ("TODO: Save results...")
        print (result)
        self.close()


    def _buildMethods(self):
        return {
            'tree': [
                treeOptions.PointCountOptions('Point Count'),
                treeOptions.BranchCountOptions('Branch Count'),
                treeOptions.TDBLOptions('TDBL')
            ],
            'branch': [
                branchOptions.BranchLengthOptions('Branch Length'),
                branchOptions.BranchTypeOptions('Branch Type'),
                branchOptions.IsAxonOptions('Is axon?'),
                branchOptions.BranchParentIDOptions('Branch Parent IDs')
            ],
            'puncta': [
                punctaOptions.PunctaSizeOptions('Puncta Size'),
                punctaOptions.PunctaIntensityOptions('Puncta intensity')
            ]
        }

    def _clearChildWidgets(self, layout):
        while layout.count() > 0:
            item = layout.itemAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
            layout.removeItem(item)
        layout.update()
        layout.parentWidget().repaint()
