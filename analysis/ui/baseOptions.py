from abc import ABC, abstractmethod

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.Qt import Qt

class BaseOptions(ABC):
    def __init__(self, name, methodToCall):
        self.name = name
        self.methodToCall = methodToCall
        self.inclusionCheck = None

    def fillOptions(self, frameLayout, currentState):
        # TODO - include/exclude option
        frameLayout.addWidget(QtWidgets.QLabel("Options for " + self.name))
        self.inclusionCheck = QtWidgets.QCheckBox("Include in analysis?")

        k = self._includeKey()
        initialState = currentState[k] if k in currentState else True
        self.inclusionCheck.setChecked(initialState)

        frameLayout.addWidget(self.inclusionCheck)

    def readOptions(self):
        return {self._includeKey(): self.inclusionCheck.isChecked()}

    def defaultValues(self):
        return {self._includeKey(): True}

    def shouldRun(self, currentState):
        k = self._includeKey()
        return (k not in currentState) or (currentState[k] == True)

    def _includeKey(self):
        return '_do ' + self.name
