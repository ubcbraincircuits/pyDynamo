from abc import ABC, abstractmethod

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.Qt import Qt

"""
Superclass for all analysis option specifications.
Holds the method to run, and whether or not to run the method during analysis.
"""
class BaseOptions(ABC):
    def __init__(self, name, methodToCall):
        """Defines basic properties allowing configuration of an analysis method.

        Args:
            name (string): What this analysis method is called.
            methodToCall (Fuction): Python code to get called if analysis is run.
        """
        self.name = name
        self.methodToCall = methodToCall
        self.inclusionCheck = None

    # Fill the options panel with the options for this method.
    # NOTE: don't need to override, use fillOptionsInner instead
    def fillOptions(self, frameLayout, fullState):
        frameLayout.addWidget(QtWidgets.QLabel("Options for " + self.name))
        self.formParent = QtWidgets.QWidget(frameLayout.parentWidget())
        self.formLayout = QtWidgets.QFormLayout(self.formParent)

        # One forced widget on all - whether or not to include in analysis.
        self.inclusionCheck = QtWidgets.QCheckBox(self.formParent)
        k = self._includeKey()
        currentState = fullState.projectOptions.analysisOptions
        self.inclusionCheck.setChecked(currentState[k] if k in currentState else True)
        self._addFormRow("Include in analysis?", self.inclusionCheck)

        self.fillOptionsInner(currentState, fullState, self.formParent)
        frameLayout.addWidget(self.formParent)

    def fillOptionsInner(self, currentState, fullState, formParent):
        """Customize the UI rendering for the options, implement in subclasses.

        Args:
            currentState (dict): Current analysis parameters configured.
            fullState (dict): Model state for the entire project
            formParent (QFormLayout): Parent layout to add widgets to.
        """
        pass

    # Read options dictionary back out from UI once done.
    def readOptions(self):
        if self.inclusionCheck is None:
            return {} # Hasn't been installed yet, skip
        return {self._includeKey(): self.inclusionCheck.isChecked()}

    # Mapping from all supported parameter names, to their default values.
    def defaultValues(self):
        return {self._includeKey(): True}

    # Whether this analysis method should run.
    def shouldRun(self, currentState):
        k = self._includeKey()
        return (k not in currentState) or (currentState[k] == True)

    # Adds a "Caption: <widget>" input pair to the form.
    def _addFormRow(self, caption, inputWidget):
        self.formLayout.addRow(caption, inputWidget)

    # Local key for tracking whether the analysis should be run.
    def _includeKey(self):
        return '_do ' + self.name
