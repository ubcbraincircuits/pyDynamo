from abc import ABC, abstractmethod

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.Qt import Qt

class BaseOptions(ABC):
    def __init__(self, name, methodToCall):
        self.name = name
        self.methodToCall = methodToCall
        self.inclusionCheck = None

    def fillOptions(self, frameLayout, currentState):
        frameLayout.addWidget(QtWidgets.QLabel("Options for " + self.name))
        self.formParent = QtWidgets.QWidget(frameLayout.parentWidget())
        self.formLayout = QtWidgets.QFormLayout(self.formParent)

        # One forced widget on all - whether or not to include in analysis.
        self.inclusionCheck = QtWidgets.QCheckBox(self.formParent)
        k = self._includeKey()
        self.inclusionCheck.setChecked(currentState[k] if k in currentState else True)
        self._addFormRow("Include in analysis?", self.inclusionCheck)

        self.fillOptionsInner(currentState, self.formParent)
        frameLayout.addWidget(self.formParent)

    def fillOptionsInner(self, currentState, formParent):
        pass

    def readOptions(self):
        # Hasn't been installed yet, skip
        if self.inclusionCheck is None:
            return {}
        return {self._includeKey(): self.inclusionCheck.isChecked()}

    def defaultValues(self):
        return {self._includeKey(): True}

    def shouldRun(self, currentState):
        k = self._includeKey()
        return (k not in currentState) or (currentState[k] == True)

    def _addFormRow(self, caption, inputWidget):
        self.formLayout.addRow(caption, inputWidget)

    def _includeKey(self):
        return '_do ' + self.name
