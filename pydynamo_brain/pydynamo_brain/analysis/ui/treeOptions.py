from .baseOptions import BaseOptions

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.Qt import Qt

from pydynamo_brain.ui.common import floatOrDefault
from pydynamo_brain.analysis.functions import tree

# Methods without custom options

class PointCountOptions(BaseOptions):
    def __init__(self, name):
        super().__init__(name, tree.pointCount)

class BranchCountOptions(BaseOptions):
    def __init__(self, name):
        super().__init__(name, tree.branchCount)

# Methods with custom options


# Parameters supported are passed to TDBL
class TDBLOptions(BaseOptions):
    def __init__(self, name):
        super().__init__(name, tree.tdbl)

    def fillOptionsInner(self, currentState, fullState, formParent):
        self.filoDist = QtWidgets.QLineEdit(formParent)
        self.filoDist.setValidator(QtGui.QDoubleValidator())
        k = 'filoDist'
        self.filoDist.setText(str(currentState[k]) if k in currentState else '10')
        self._addFormRow("Filopodia dist (uM)", self.filoDist)

        self.includeFilo = QtWidgets.QCheckBox(formParent)
        k = 'includeFilo'
        self.includeFilo.setChecked(currentState[k] if k in currentState else True)
        self._addFormRow("Include filopodia?", self.includeFilo)

        self.excludeAxon = QtWidgets.QCheckBox(formParent)
        k = 'excludeAxon'
        self.excludeAxon.setChecked(currentState[k] if k in currentState else True)
        self._addFormRow("Exclude Axon?", self.excludeAxon)

        self.excludeBasal = QtWidgets.QCheckBox(formParent)
        k = 'excludeBasal'
        self.excludeBasal.setChecked(currentState[k] if k in currentState else True)
        self._addFormRow("Exclude Basal?", self.excludeBasal)

    def readOptions(self):
        localOptions = {
            'filoDist': floatOrDefault(self.filoDist, 10.0),
            'includeFilo': self.includeFilo.isChecked(),
            'excludeAxon': self.excludeAxon.isChecked(),
            'excludeBasal': self.excludeBasal.isChecked()
        }
        localOptions.update(super().readOptions())
        return localOptions

    def defaultValues(self):
        return {
            'filoDist': 10.0,
            'includeFilo': True,
            'excludeAxon': True,
            'excludeBasal': True
        }

# These parameters are passed to sholl analysis
class ShollOptions(BaseOptions):
    def __init__(self, name):
        super().__init__(name, tree.shollStats)

    def fillOptionsInner(self, currentState, fullState, formParent):
        self.binSize = QtWidgets.QLineEdit(formParent)
        self.binSize.setValidator(QtGui.QDoubleValidator())
        k = 'shollBinSize'
        self.binSize.setText(str(currentState[k]) if k in currentState else '5.0')
        self._addFormRow("Sholl Bin Size (uM)", self.binSize)

    def readOptions(self):
        localOptions = {
            'shollBinSize': floatOrDefault(self.binSize, 5.0),
        }
        localOptions.update(super().readOptions())
        return localOptions

    def defaultValues(self):
        return {
            'shollBinSize': 5.0,
        }

# Parameters supported are passed to motility
class MotilityOptions(BaseOptions):
    def __init__(self, name):
        super().__init__(name, tree.motility)

    def fillOptionsInner(self, currentState, fullState, formParent):
        self.filoDist = QtWidgets.QLineEdit(formParent)
        self.filoDist.setValidator(QtGui.QDoubleValidator())
        k = 'filoDist'
        self.filoDist.setText(str(currentState[k]) if k in currentState else '10')
        self._addFormRow("Filopodia dist (uM)", self.filoDist)

        self.terminalDist = QtWidgets.QLineEdit(formParent)
        self.terminalDist.setValidator(QtGui.QDoubleValidator())
        k = 'terminalDist'
        self.terminalDist.setText(str(currentState[k]) if k in currentState else '10')
        self._addFormRow("Terminal filo dist (uM)", self.terminalDist)

        self.excludeAxon = QtWidgets.QCheckBox(formParent)
        k = 'excludeAxon'
        self.excludeAxon.setChecked(currentState[k] if k in currentState else True)
        self._addFormRow("Exclude Axon?", self.excludeAxon)

        self.excludeBasal = QtWidgets.QCheckBox(formParent)
        k = 'excludeBasal'
        self.excludeBasal.setChecked(currentState[k] if k in currentState else True)
        self._addFormRow("Exclude Basal?", self.excludeBasal)

    def readOptions(self):
        localOptions = {
            'filoDist': floatOrDefault(self.filoDist, 10.0),
            'terminalDist': floatOrDefault(self.terminalDist, 10.0),
            'excludeAxon': self.excludeAxon.isChecked(),
            'excludeBasal': self.excludeBasal.isChecked()
        }
        localOptions.update(super().readOptions())
        return localOptions

    def defaultValues(self):
        return {
            'filoDist': 10.0,
            'terminalDist': 10.0,
            'excludeAxon': True,
            'excludeBasal': True,
        }
