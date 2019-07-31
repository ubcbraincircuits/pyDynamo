import math
import numpy as np

import pydynamo_brain.util as util

from PyQt5 import QtCore, QtWidgets
from PyQt5.Qt import Qt

from .common import cursorPointer

class _SizedListWidget(QtWidgets.QListWidget):
    """Helper list widget which takes up as much space as its children combined."""
    def sizeHint(self):
        s = QtCore.QSize()
        s.setWidth(self.sizeHintForColumn(0) + 2 * self.frameWidth())
        s.setHeight(self.sizeHintForRow(0) * self.count() + 2 * self.frameWidth())
        return s

class StackListWindow(QtWidgets.QMainWindow):
    """Window that shows all stacks, and gives options to show/hide plus delete them."""

    def __init__(self, parent):
        QtWidgets.QMainWindow.__init__(self, parent)
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.CustomizeWindowHint | QtCore.Qt.WindowStaysOnTopHint)
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowCloseButtonHint)
        self.setWindowTitle("Stack List")

        self.list = _SizedListWidget()
        self.root = QtWidgets.QWidget(self)

        # Bring-to-front button
        self.toFrontButton = QtWidgets.QPushButton("Bring visible to front", self)
        self.toFrontButton.setToolTip("Make all shown windows visible")
        self.toFrontButton.clicked.connect(self.bringToFront)

        l = QtWidgets.QVBoxLayout(self.root)
        l.setContentsMargins(0, 0, 0, 0)
        l.addWidget(self.toFrontButton)
        l.addWidget(self.list)
        self.setCentralWidget(self.root)
        self.updateListFromStacks()

    def updateListFromStacks(self):
        """Update the window's data to reflect the current values in the app."""
        p = self.parent()
        n = len(p.stackWindows)
        assert n == len(p.fullState.uiStates)

        # Clear, add all items, and resize to fit:
        self.list.clear()
        for i in range(n):
            self._addItem(i, p.fullState.filePaths[i], p.fullState.uiStates[i].isHidden)
        listSize = self.list.sizeHint()
        buttonSize = self.toFrontButton.sizeHint()
        combined = QtCore.QSize()
        combined.setWidth(max(listSize.width(), buttonSize.width()))
        combined.setHeight(listSize.height() + buttonSize.height() + 20) # 20 extra for padding
        self.list.resize(listSize)
        self.resize(combined)

    def bringToFront(self):
        """Goes through each visible stack window, and if not hidden, bring to front."""
        p = self.parent()
        for i, stackWindow in enumerate(p.stackWindows):
            if not p.fullState.uiStates[i].isHidden:
                stackWindow.show()
                stackWindow.raise_()

    def _addItem(self, idx, filePath, stackHidden):
        """Adds a single row into the list, and attaches events."""
        title = util.createTitle(idx, filePath)

        # Build the widget itself.
        container = QtWidgets.QWidget()
        wText =  QtWidgets.QLabel(title)
        bViz = QtWidgets.QPushButton("Show" if stackHidden else "Hide")
        bDel = QtWidgets.QPushButton("Delete")
        l = QtWidgets.QHBoxLayout()
        l.addWidget(wText)
        l.addWidget(bViz)
        l.addWidget(bDel)
        l.addStretch()
        l.setSizeConstraint(QtWidgets.QLayout.SetFixedSize)
        container.setLayout(l)

        # Build the list item, and add the widget:
        itemN = QtWidgets.QListWidgetItem()
        itemN.setSizeHint(container.sizeHint())
        self.list.addItem(itemN)
        self.list.setItemWidget(itemN, container)

        # Attach events:
        bViz.clicked.connect(lambda: self._handleVizChange(idx))
        bDel.clicked.connect(lambda: self._handleDelete(idx, title))

    def _handleVizChange(self, idx):
        """Handle the 'show'/'hide' option selection for a stack."""
        self.parent().toggleStackWindowVisibility(idx)

    def _handleDelete(self, idx, title):
        """Handle the 'delete' option selection for a stack."""
        msg = "Delete all data for %s?" % title
        reply = QtWidgets.QMessageBox.question(
            self, 'Remove stack?', msg, QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No
        )
        if reply == QtWidgets.QMessageBox.Yes: # Confirm first! This deletes a lot of data.
            self.parent().removeStackWindow(idx, deleteData=True)