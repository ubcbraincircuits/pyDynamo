import math
import numpy as np

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.Qt import Qt

from pydynamo_brain.model import MotilityOptions, ProjectOptions

from .common import centerWindow, cursorPointer, floatOrDefault

class SettingsWindow(QtWidgets.QMainWindow):
    def __init__(self, parent):
        QtWidgets.QMainWindow.__init__(self, parent)

        self.setWindowTitle("Project settings")
        centerWindow(self)

        # Fields for Pixel x/y/z
        self.xValue = QtWidgets.QLineEdit()
        self.xValue.setValidator(QtGui.QDoubleValidator(0, 10, 5))
        self.yValue = QtWidgets.QLineEdit()
        self.yValue.setValidator(QtGui.QDoubleValidator(0, 10, 5))
        self.zValue = QtWidgets.QLineEdit()
        self.zValue.setValidator(QtGui.QDoubleValidator(0, 30, 5))

        # Fields for motility options:
        self.filoDist = QtWidgets.QLineEdit()
        self.filoDist.setValidator(QtGui.QDoubleValidator(0, 20, 1))
        self.terminalDist = QtWidgets.QLineEdit()
        self.terminalDist.setValidator(QtGui.QDoubleValidator(0, 20, 1))
        self.minMotilityDist = QtWidgets.QLineEdit()
        self.minMotilityDist.setValidator(QtGui.QDoubleValidator(0, 5, 2))
        self.excludeAxon = QtWidgets.QCheckBox()
        self.excludeBasal = QtWidgets.QCheckBox()
        self.includeAS = QtWidgets.QCheckBox()

        # Fields for misc options:
        self.shollBinSize = QtWidgets.QLineEdit()
        self.shollBinSize.setValidator(QtGui.QDoubleValidator(0, 20, 3))

        # Root = vertical layout
        self.root = QtWidgets.QWidget(self)
        l = QtWidgets.QVBoxLayout(self.root)

        # First up: Pixel x/y/z size in microns
        pixelSizes = QtWidgets.QWidget(self)
        l1 = QtWidgets.QFormLayout(pixelSizes)
        l1.addRow("X (μM)", self.xValue)
        l1.addRow("Y (μM)", self.yValue)
        l1.addRow("Z (μM)", self.zValue)

        # Next up: Options for motility plot
        motOptions = QtWidgets.QWidget(self)
        l2 = QtWidgets.QFormLayout(motOptions)
        l2.addRow("Max Filopodia length (μM)", self.filoDist)
        l2.addRow("Max Terminal length (μM)", self.terminalDist)
        l2.addRow("Min motility distance (μM)", self.minMotilityDist)
        l2.addRow("Exclude Axon?", self.excludeAxon)
        l2.addRow("Exclude Basal dendrites?", self.excludeBasal)
        l2.addRow("Include Branch addition/subtraction?", self.includeAS)

        # Next: Misc
        otherOptions = QtWidgets.QWidget(self)
        l3 = QtWidgets.QFormLayout(otherOptions)
        l3.addRow("Sholl bin size (μM)", self.shollBinSize)

        # And finally, buttons:
        bCancel = QtWidgets.QPushButton("Cancel", self)
        bCancel.clicked.connect(self.cancelOptions)
        cursorPointer(bCancel)
        bSave = QtWidgets.QPushButton("Save", self)
        bSave.clicked.connect(self.saveOptions)
        cursorPointer(bSave)

        buttons = QtWidgets.QWidget(self)
        lB = QtWidgets.QHBoxLayout(buttons)
        lB.addStretch()
        lB.addWidget(bSave)
        lB.addStretch()
        lB.addWidget(bCancel)
        lB.addStretch()

        l.addWidget(QtWidgets.QLabel("Pixel sizes"))
        l.addWidget(pixelSizes)
        l.addWidget(QtWidgets.QLabel("Added/Subtracted/Transitioned options"))
        l.addWidget(motOptions)
        l.addWidget(QtWidgets.QLabel("Other options"))
        l.addWidget(otherOptions)
        l.addWidget(buttons)

        self.root.setFocus()
        self.setCentralWidget(self.root)

    def openFromState(self, fullState):
        self.fullState = fullState

        self.xValue.setText("%.3f" % fullState.projectOptions.pixelSizes[0])
        self.yValue.setText("%.3f" % fullState.projectOptions.pixelSizes[1])
        self.zValue.setText("%.3f" % fullState.projectOptions.pixelSizes[2])

        motOpt = fullState.projectOptions.motilityOptions
        self.filoDist.setText("%.1f" % motOpt.filoDist)
        self.terminalDist.setText("%.1f" % motOpt.terminalDist)
        self.minMotilityDist.setText("%.2f" % motOpt.minMotilityDist)
        self.excludeAxon.setChecked(motOpt.excludeAxon)
        self.excludeBasal.setChecked(motOpt.excludeBasal)
        self.includeAS.setChecked(motOpt.includeAS)

        analysisOpt = fullState.projectOptions.analysisOptions
        shollSize = analysisOpt['shollBinSize'] if 'shollBinSize' in analysisOpt else 5.0
        self.shollBinSize.setText("%.3f" % shollSize)

        self.show()

    def saveOptions(self):
        self.fullState.projectOptions = self.buildProjectOptions()
        self.fullState = None
        self.close()

    def cancelOptions(self):
        self.fullState = None
        self.close()

    ### Copy fields into options model objects.
    def buildProjectOptions(self):
        options = ProjectOptions()
        options.pixelSizes = [
            floatOrDefault(self.xValue, 0.307),
            floatOrDefault(self.yValue, 0.307),
            floatOrDefault(self.zValue, 1.5)
        ]
        options.motilityOptions = self.buildMotilityOptions()
        # TODO - split into buildAnalysisOptions if more get added here...
        options.analysisOptions['shollBinSize'] = floatOrDefault(self.shollBinSize, 5.0)
        return options

    def buildMotilityOptions(self):
        options = MotilityOptions()
        options.filoDist = floatOrDefault(self.filoDist, 5)
        options.terminalDist = floatOrDefault(self.terminalDist, 5)
        options.minMotilityDist = floatOrDefault(self.minMotilityDist, 0.1)
        options.excludeAxon = self.excludeAxon.isChecked()
        options.excludeBasal = self.excludeBasal.isChecked()
        options.includeAS = self.includeAS.isChecked()
        return options
