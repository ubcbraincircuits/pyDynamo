from .baseOptions import BaseOptions

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.Qt import Qt

from ui.common import floatOrDefault
from ..functions import branch

# Methods without custom options

class BranchLengthOptions(BaseOptions):
    def __init__(self, name):
        super().__init__(name, branch.branchLengths)

class IsAxonOptions(BaseOptions):
    def __init__(self, name):
        super().__init__(name, branch.branchHasAnnotationFunc('axon'))

class BranchParentIDOptions(BaseOptions):
    def __init__(self, name):
        super().__init__(name, branch.branchParentIDs)

# Methods with custom options

class BranchTypeOptions(BaseOptions):
    # Parameters supported are passed to addedSubtractedTransitioned
    def __init__(self, name):
        super().__init__(name, branch.branchType)

    def fillOptionsInner(self, currentState, formParent):
        self.filoDist = QtWidgets.QLineEdit(formParent)
        k = 'filoDist'
        self.filoDist.setText(str(currentState[k]) if k in currentState else '10')
        self._addFormRow("Filopodia dist (uM)", self.filoDist)

        self.terminalDist = QtWidgets.QLineEdit(formParent)
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
            'excludeBasal': True
        }
