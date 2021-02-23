from PyQt5 import QtCore, QtWidgets

import numpy as np
import pyneurotrace.filters as filters

from .allTracesCanvas import AllTracesCanvas

# Plot view showing traces associated to all selected points.
class AllTracesWindow(QtWidgets.QMainWindow):
    def __init__(self, parent, fullState, treeIdx):
        super(AllTracesWindow, self).__init__(parent)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowTitle('Traces')

        filterMenu = QtWidgets.QMenu('Filters', self)
        self.okadaToggle = QtWidgets.QAction('Okada', filterMenu, checkable=True, checked=True)
        self.dfof0Toggle = QtWidgets.QAction('DF/F0', filterMenu, checkable=True, checked=True)
        self.nndSmoothToggle = QtWidgets.QAction('NND Smooth', filterMenu, checkable=True, checked=False)
        for toggle in [self.okadaToggle, self.dfof0Toggle, self.nndSmoothToggle]:
            filterMenu.addAction(toggle)
            toggle.triggered.connect(self._filtersChangeEvent)


        self.view = AllTracesCanvas(self, fullState, treeIdx)

        root = QtWidgets.QWidget(self)
        l = QtWidgets.QHBoxLayout(root)
        l.setContentsMargins(0, 0, 0, 0)
        l.addWidget(self.view)
        root.setFocus()
        self.setCentralWidget(root)

        self.menuBar().addMenu(filterMenu)

    def _filtersChangeEvent(self):
        self.view.needToUpdate()

    def applyFilters(self, trace, hz):
        # These filters assume multiple rows, make into a single row:
        trace = np.expand_dims(trace, axis=0)

        # TODO: support parameters for these in project options?
        if self.okadaToggle.isChecked():
            trace = filters.okada(trace)
        if self.dfof0Toggle.isChecked():
            trace = filters.deltaFOverF0(trace, int(hz))
        if self.nndSmoothToggle.isChecked():
            trace = filters.nndSmooth(trace, hz, tau=0.75)

        return trace[0] # Extract back single row.

    def getTitle(self):
        prefix = "Smoothed " if self.nndSmoothToggle.isChecked() else ""
        suffix = "DF/F0" if self.dfof0Toggle.isChecked() else "Raw"
        return prefix + suffix
