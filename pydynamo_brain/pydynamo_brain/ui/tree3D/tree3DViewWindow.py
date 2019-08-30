from PyQt5 import QtWidgets

from pydynamo_brain.ui.scrollableStacksWindow import ScrollableStacksWindow

from .tree3DCanvas import Tree3DCanvas

# Scrollable list of stacks, showing 3D moveable view of the tree structures.
class Tree3DViewWindow(ScrollableStacksWindow):
    def __init__(self, parent, fullState, firstTreeIdx, treeModels, filePaths):
        super().__init__(parent, treeModels, '3D Arbor',
            Tree3DCanvas(parent, fullState, firstTreeIdx, treeModels, filePaths),
            treesShown=Tree3DCanvas.TREE_COUNT
        )

        viewMenu = QtWidgets.QMenu('View', self)
        self._addScrollActions(viewMenu)
        self.menuBar().addMenu(viewMenu)
