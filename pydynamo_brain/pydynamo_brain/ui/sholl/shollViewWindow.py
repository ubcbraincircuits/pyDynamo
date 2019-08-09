from PyQt5 import QtWidgets

from pydynamo_brain.ui.scrollableStacksWindow import ScrollableStacksWindow

from .shollCanvas import ShollCanvas

# TODO:
# -) Analysis code for export
# -) Move motitility/registration to child folders
# -) Extract common mot/reg/sholl view code

# Metrics to include:
#   * Max value of N
#   * Radius at max value
#   * Fitted for polynomial degree = k
#   * Schoenen Ramification = max value / primary dendrites
#   * # crossings

# Scrollable list of stacks, showing registration between stack pairs.
class ShollViewWindow(ScrollableStacksWindow):
    def __init__(self, parent, fullState, firstTreeIdx, treeModels, filePaths):
        super().__init__(parent, treeModels, 'Sholl Analysis',
            ShollCanvas(parent, fullState, firstTreeIdx, treeModels, filePaths),
            treesShown=ShollCanvas.TREE_COUNT
        )

        viewMenu = QtWidgets.QMenu('View', self)
        self._addScrollActions(viewMenu)
        self.menuBar().addMenu(viewMenu)
