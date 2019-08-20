from PyQt5 import QtCore, QtWidgets

from pydynamo_brain.ui.scrollableStacksWindow import ScrollableStacksWindow

from .registration3DCanvas import Registration3DCanvas

# Scrollable list of stacks, showing registration between stack pairs.
class Registration3DViewWindow(ScrollableStacksWindow):
    def __init__(self, parent, firstTreeIdx, treeModels, filePaths):
        super().__init__(parent, treeModels, 'Point Registration',
            Registration3DCanvas(parent, firstTreeIdx, treeModels, filePaths),
            treesShown=3
        )

        viewMenu = QtWidgets.QMenu('View', self)
        self._addScrollActions(viewMenu)
        self.menuBar().addMenu(viewMenu)
