from .baseOptions import BaseOptions

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.Qt import Qt

from typing import Any, Dict

from pydynamo_brain.analysis.functions import branch
from pydynamo_brain.model import FullState
from pydynamo_brain.ui.common import floatOrDefault

# Methods without custom options

class BranchLengthOptions(BaseOptions):
    def __init__(self, name: str) -> None:
        super().__init__(name, branch.branchLengths)

class IsAxonOptions(BaseOptions):
    def __init__(self, name: str) -> None:
        super().__init__(name, branch.branchHasAnnotationFunc('axon', recurseUp=True))

class IsBasalOptions(BaseOptions):
    def __init__(self, name: str) -> None:
        super().__init__(name, branch.branchHasAnnotationFunc('basal', recurseUp=True))

class BranchParentIDOptions(BaseOptions):
    def __init__(self, name: str) -> None:
        super().__init__(name, branch.branchParentIDs)

# Methods with custom options

class BranchTypeOptions(BaseOptions):
    # Parameters supported are passed to addedSubtractedTransitioned
    def __init__(self, name: str) -> None:
        super().__init__(name, branch.branchType)

    def fillOptionsInner(self,
        currentState: Dict[str, Any], fullState: FullState, formParent: QtWidgets.QWidget
    ) -> None:
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

    def readOptions(self) -> Dict[str, Any]:
        localOptions = {
            'filoDist': floatOrDefault(self.filoDist, 10.0),
            'terminalDist': floatOrDefault(self.terminalDist, 10.0),
            'excludeAxon': self.excludeAxon.isChecked(),
            'excludeBasal': self.excludeBasal.isChecked()
        }
        localOptions.update(super().readOptions())
        return localOptions

    def defaultValues(self) -> Dict[str, Any]:
        return {
            'filoDist': 10.0,
            'terminalDist': 10.0,
            'excludeAxon': True,
            'excludeBasal': True
        }


# Type of branch order, whether it's centrifugal (default) or shaft
class BranchOrderOptions(BaseOptions):
    def __init__(self, name: str) -> None:
        super().__init__(name, branch.branchOrder)

    def fillOptionsInner(self,
        currentState: Dict[str, Any], fullState: FullState, formParent: QtWidgets.QWidget
    ) -> None:
        self.shaftOrder = QtWidgets.QCheckBox(formParent)
        k = 'shaftOrder'
        self.shaftOrder.setChecked(currentState[k] if k in currentState else False)
        self._addFormRow("Shaft order?", self.shaftOrder)

    def readOptions(self) -> Dict[str, Any]:
        localOptions = {
            'shaftOrder': self.shaftOrder.isChecked(),
        }
        localOptions.update(super().readOptions())
        return localOptions

    def defaultValues(self) -> Dict[str, Any]:
        return {
            'shaftOrder': False,
        }
