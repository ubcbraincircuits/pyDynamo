from PyQt5 import QtWidgets

from pydynamo_brain.ui.scrollableStacksWindow import ScrollableStacksWindow

from .shollCanvas import ShollCanvas

# TODO:
# -) Cache results
# -) Save image
# -) Bin count config
# -) Shortcut?
# -) Metrics
# -) Analysis code for export
# -) Move motitility/registration to child folders
# -) Extract common mot/reg/sholl view code

# Scrollable list of stacks, showing registration between stack pairs.
class ShollViewWindow(ScrollableStacksWindow):
    def __init__(self, parent, firstTreeIdx, treeModels, filePaths):
        super().__init__(parent, treeModels, 'Point Registration',
            ShollCanvas(parent, firstTreeIdx, treeModels, filePaths),
            treesShown=ShollCanvas.TREE_COUNT
        )

        viewMenu = QtWidgets.QMenu('View', self)
        self._addScrollActions(viewMenu)
        self.menuBar().addMenu(viewMenu)
