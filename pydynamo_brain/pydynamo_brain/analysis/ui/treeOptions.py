from .baseOptions import BaseOptions

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.Qt import Qt

from typing import Any, Callable, Dict

from pydynamo_brain.analysis.functions import tree
from pydynamo_brain.model import FullState
from pydynamo_brain.ui.common import floatOrDefault

# Methods without custom options

class PointCountOptions(BaseOptions):
    def __init__(self, name: str) -> None:
        super().__init__(name, tree.pointCount)

class BranchCountOptions(BaseOptions):
    def __init__(self, name: str) -> None:
        super().__init__(name, tree.branchCount)

# Methods with custom options


# Parameters supported are passed to TDBL
class TDBLOptions(BaseOptions):
    def __init__(self, name: str) -> None:
        super().__init__(name, tree.tdbl)

    def fillOptionsInner(self,
        currentState: Dict[str, Any], fullState: FullState, formParent: QtWidgets.QWidget
    ) -> None:
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

    def readOptions(self) -> Dict[str, Any]:
        localOptions = {
            'filoDist': floatOrDefault(self.filoDist, 10.0),
            'includeFilo': self.includeFilo.isChecked(),
            'excludeAxon': self.excludeAxon.isChecked(),
            'excludeBasal': self.excludeBasal.isChecked()
        }
        localOptions.update(super().readOptions())
        return localOptions

    def defaultValues(self) -> Dict[str, Any]:
        return {
            'filoDist': 10.0,
            'includeFilo': True,
            'excludeAxon': True,
            'excludeBasal': True
        }

# These parameters are passed to sholl analysis
class ShollOptions(BaseOptions):
    def __init__(self, name: str) -> None:
        super().__init__(name, tree.shollStats)

    def fillOptionsInner(self,
        currentState: Dict[str, Any], fullState: FullState, formParent: QtWidgets.QWidget
    ) -> None:
        self.binSize = QtWidgets.QLineEdit(formParent)
        self.binSize.setValidator(QtGui.QDoubleValidator())
        k = 'shollBinSize'
        self.binSize.setText(str(currentState[k]) if k in currentState else '5.0')
        self._addFormRow("Sholl Bin Size (uM)", self.binSize)

    def readOptions(self) -> Dict[str, Any]:
        localOptions = {
            'shollBinSize': floatOrDefault(self.binSize, 5.0),
        }
        localOptions.update(super().readOptions())
        return localOptions

    def defaultValues(self) -> Dict[str, Any]:
        return {
            'shollBinSize': 5.0,
        }

# Parameters supported are passed to motility
class MotilityOptions(BaseOptions):
    def __init__(self, name: str, methodToCall: Callable=tree.motility) -> None:
        super().__init__(name, methodToCall)

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
            'excludeBasal': True,
        }

# Filo count & density, same as motility, just different method:
class FiloCountOptions(MotilityOptions):
    def __init__(self, name: str) -> None:
        super().__init__(name, tree.filoCount)

class FiloDensityOptions(MotilityOptions):
    def __init__(self, name: str) -> None:
        # NOTE: TDBL also called, should get default includeFilo=True
        super().__init__(name, tree.filoDensity)
