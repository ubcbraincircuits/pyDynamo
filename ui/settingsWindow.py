import math
import numpy as np

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.Qt import Qt

class SettingsWindow(QtWidgets.QMainWindow):
    def __init__(self, parent):
        QtWidgets.QMainWindow.__init__(self, parent)

        self.setWindowTitle("Project settings")
        self.centerWindow()

        # Fields for Pixel x/y/z
        self.xValue = QtWidgets.QLineEdit()
        self.xValue.setValidator(QtGui.QDoubleValidator(0, 10, 3))
        self.yValue = QtWidgets.QLineEdit()
        self.yValue.setValidator(QtGui.QDoubleValidator(0, 10, 3))
        self.zValue = QtWidgets.QLineEdit()
        self.zValue.setValidator(QtGui.QDoubleValidator(0, 30, 3))

        # Fields for motility options:
        self.filoDist = QtWidgets.QLineEdit()
        self.filoDist.setValidator(QtGui.QDoubleValidator(0, 20, 1))
        self.terminalDist = QtWidgets.QLineEdit()
        self.terminalDist.setValidator(QtGui.QDoubleValidator(0, 20, 1))
        self.excludeAxon = QtWidgets.QCheckBox()
        self.excludeBasal = QtWidgets.QCheckBox()
        self.includeAS = QtWidgets.QCheckBox()

        # Root = vertical layout
        self.root = QtWidgets.QWidget(self)
        l = QtWidgets.QVBoxLayout(self.root)

        # First up: Pixel x/y/z size in microns
        pixelSizes = QtWidgets.QWidget(self)
        l1 = QtWidgets.QFormLayout()
        l1.addRow("X (μM)", self.xValue)
        l1.addRow("Y (μM)", self.yValue)
        l1.addRow("Z (μM)", self.zValue)
        pixelSizes.setLayout(l1)

        # Next up: Options for motility plot
        motOptions = QtWidgets.QWidget(self)
        l2 = QtWidgets.QFormLayout()
        l2.addRow("Max Filopodia length (μM)", self.filoDist)
        l2.addRow("Max Terminal length (μM)", self.terminalDist)
        l2.addRow("Exclude Axon?", self.excludeAxon)
        l2.addRow("Exclude Basal dendrites?", self.excludeBasal)
        l2.addRow("Include Branch addition/subtraction?", self.includeAS)
        motOptions.setLayout(l2)

        l.addWidget(QtWidgets.QLabel("Pixel sizes"))
        l.addWidget(pixelSizes)
        l.addWidget(QtWidgets.QLabel("Added/Subtracted/Transitioned options"))
        l.addWidget(motOptions)

        self.buttons = QtWidgets.QWidget(self)
        l3 = QtWidgets.QVBoxLayout(self.root)
        

        self.root.setFocus()
        self.setCentralWidget(self.root)


    def openFromState(self, fullState):
        print ("Opening")
        self.xValue.setText("%.3f" % fullState.projectOptions.pixelSizes[0])
        self.yValue.setText("%.3f" % fullState.projectOptions.pixelSizes[1])
        self.zValue.setText("%.3f" % fullState.projectOptions.pixelSizes[2])

        motOpt = fullState.projectOptions.motilityOptions
        self.filoDist.setText("%.1f" % motOpt.filoDist)
        self.terminalDist.setText("%.1f" % motOpt.terminalDist)
        self.excludeAxon.setChecked(motOpt.excludeAxon)
        self.excludeBasal.setChecked(motOpt.excludeBasal)
        self.includeAS.setChecked(motOpt.includeAS)
        self.show()

    def centerWindow(self):
        # self.setFixedSize(480, 320)
        frameGm = self.frameGeometry()
        centerPoint = QtWidgets.QDesktopWidget().availableGeometry().center()
        frameGm.moveCenter(centerPoint)
        self.move(frameGm.topLeft())

    """
    def keyPressEvent(self, event):
        self.parent().keyPressEvent(event)
    """
