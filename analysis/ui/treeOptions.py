from .baseOptions import BaseOptions

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.Qt import Qt

from ..functions import tree

# Methods without custom options

class PointCountOptions(BaseOptions):
    def __init__(self, name):
        super().__init__(name, tree.pointCount)

class BranchCountOptions(BaseOptions):
    def __init__(self, name):
        super().__init__(name, tree.branchCount)

# Methods with custom options

class TDBLOptions(BaseOptions):
    def __init__(self, name):
        super().__init__(name, tree.tdbl)

    def fillOptionsInner(self, currentState, formParent):
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
            'filoDist': float(self.filoDist.text()),
            'includeFilo': self.includeFilo.isChecked(),
            'excludeAxon': self.excludeAxon.isChecked(),
            'excludeBasal': self.excludeBasal.isChecked()
        }
        localOptions.update(super().readOptions())
        return localOptions

    def defaultValues(self):
        return {
            'filoDist': 10,
            'includeFilo': True,
            'excludeAxon': True,
            'excludeBasal': True
        }
