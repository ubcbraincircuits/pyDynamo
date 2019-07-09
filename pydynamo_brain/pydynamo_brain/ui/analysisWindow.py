import math
import numpy as np
import pandas as pd

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.Qt import Qt

from analysis import allTrees, allBranches, allPuncta
from analysis.ui import branchOptions, punctaOptions, treeOptions
from model import MotilityOptions, ProjectOptions

from .common import centerWindow, clearChildWidgets, cursorPointer, floatOrDefault

"""
Window containing all parameters required for performing analysis,
as well as allowing selection of what to run, and saving the results to file.
"""
class AnalysisWindow(QtWidgets.QMainWindow):
    def __init__(self, parent):
        QtWidgets.QMainWindow.__init__(self, parent)
        self.root = QtWidgets.QWidget(self)
        self.layout = QtWidgets.QVBoxLayout(self.root)
        self.lastOption = None

        # Load options from state, and insert any missing values:
        self.analysisMethods = self._buildMethods()
        for methodsPerType in self.analysisMethods.values():
            for method in methodsPerType:
                for k, v in method.defaultValues().items():
                    if k not in self.getOpt():
                        self.getOpt()[k] = v

        # Build up tabs per analysis type:
        tabTree, self.listTree, self.optTreeLayout = self._buildTab('tree')
        tabBranch, self.listBranch, self.optBranchLayout = self._buildTab('branch')
        tabPuncta, self.listPuncta, self.optPunctaLayout = self._buildTab('puncta')

        self.tabs = QtWidgets.QTabWidget()
        self.tabs.addTab(tabTree, "Tree analysis")
        self.tabs.addTab(tabBranch, "Branch analysis")
        self.tabs.addTab(tabPuncta, "Puncta analysis")
        self.tabs.currentChanged.connect(self.tabChanged)
        self.layout.addWidget(self.tabs)

        # Button to actually run the analysis
        bRun = cursorPointer(QtWidgets.QPushButton("Run analysis", self))
        bRun.clicked.connect(self.runAnalysis)
        bRun.setMaximumWidth(200)
        self.layout.addWidget(bRun, 0, QtCore.Qt.AlignRight)

        self.root.setFocus()
        self.setCentralWidget(self.root)

        self.resize(800, 600)
        self.setWindowTitle("Analysis")
        centerWindow(self)

    # Maps the analysis types, to the methods available for that type.
    def _buildMethods(self):
        return {
            'tree': [
                treeOptions.PointCountOptions('Point Count'),
                treeOptions.BranchCountOptions('Branch Count'),
                treeOptions.TDBLOptions('TDBL'),
                treeOptions.MotilityOptions('Motility'),
            ],
            'branch': [
                branchOptions.BranchLengthOptions('Branch Length'),
                branchOptions.BranchTypeOptions('Branch Type'),
                branchOptions.IsAxonOptions('Is axon?'),
                branchOptions.BranchParentIDOptions('Branch Parent IDs'),
            ],
            'puncta': [
                punctaOptions.PunctaSizeOptions('Puncta Size'),
                punctaOptions.PunctaIntensityOptions('Puncta intensity'),
            ]
        }

    # Utility for building a tab given a list of analysis methods.
    def _buildTab(self, tabType):
        tabRoot = QtWidgets.QWidget(self.root)
        tabLayout = QtWidgets.QHBoxLayout(tabRoot)

        tabList = QtWidgets.QListWidget(tabRoot)
        for method in self.analysisMethods[tabType]:
            self._addItem(tabList, method)
        tabList.currentItemChanged.connect(self._updateOnChange)

        tabOptions = QtWidgets.QFrame(tabRoot)
        tabOptions.setFrameStyle(QtWidgets.QFrame.Box | QtWidgets.QFrame.Raised)
        tabOptions.setLineWidth(2)
        tabOptions.setFixedSize(400, 500)
        tabOptionsLayout = QtWidgets.QVBoxLayout(tabOptions)

        tabLayout.addWidget(tabList)
        tabLayout.addWidget(tabOptions)
        return tabRoot, tabList, tabOptionsLayout

    # Utility for adding an analysis method to a ListWidget.
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
        itemN.setData(Qt.UserRole, method)
        listWidget.addItem(itemN)
        listWidget.setItemWidget(itemN, container)

    # Whenever the selected method changes, update the options based of the UI
    def _updateOnChange(self):
        if self.lastOption is not None:
            self.getOpt().update(self.lastOption.readOptions())

        selected = self.tabs.currentIndex()
        if selected == 0:
            item = self.listTree.currentItem()
            optLayout = self.optTreeLayout
        elif selected == 1:
            item = self.listBranch.currentItem()
            optLayout = self.optBranchLayout
        else:
            item = self.listPuncta.currentItem()
            optLayout = self.optPunctaLayout

        if item is not None:
            # Clear out the old UI options, and re-fill with the new method.
            clearChildWidgets(optLayout)
            method = item.data(Qt.UserRole)
            method.fillOptions(optLayout, self.parent().fullState)
            optLayout.addStretch(1)
            self.lastOption = method
        else:
            self.lastOption = None

    # Performs the analysis, based on the current selected tab.
    def runAnalysis(self):
        # Save recent changes first...
        if self.lastOption is not None:
            self.getOpt().update(self.lastOption.readOptions())
        self.lastOption = None

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

        # Only keep methods that the user wants to run.
        selectedFunctions = []
        for method in methods:
            if method.shouldRun(self.getOpt()):
                selectedFunctions.append(method.methodToCall)

        # Filter out internal (de)selection markers
        filteredOptions = {}
        for k, v in self.getOpt().items():
            if "_do " not in k:
                filteredOptions[k] = v

        fullState = self.parent().fullState
        resultDF = runner(fullState, selectedFunctions, **filteredOptions)
        filePath, _ = QtWidgets.QFileDialog.getSaveFileName(self,
            "Output for results", "", "CSV (*.csv)"
        )
        if filePath != "":
            if not filePath.endswith(".csv"):
                filePath = filePath + ".csv"
            resultDF.to_csv(filePath)
            QtWidgets.QMessageBox.information(self, "Saved", "Data saved to " + filePath)
        self.close()

    # Short-hand for getting the options dictionary
    def getOpt(self):
        return self.parent().fullState.projectOptions.analysisOptions

    # All events where the selected tab changes, so force options to be updated.
    def showEvent(self, ev):
        self._updateOnChange()
    def tabChanged(self, ev):
        self._updateOnChange()
