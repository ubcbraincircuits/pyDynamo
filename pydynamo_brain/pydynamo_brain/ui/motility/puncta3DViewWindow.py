from PyQt5 import QtCore, QtWidgets

from pydynamo_brain.ui.scrollableStacksWindow import ScrollableStacksWindow

from .puncta3DCanvas import Puncta3DCanvas

# Scrollable list of stacks, showing motility in the stack, in 2D or 3D.
class Puncta3DViewWindow(ScrollableStacksWindow):
    def __init__(self, parent, middleIdx, treeModels, fulllstate, filePaths, opt):
        super().__init__(parent, treeModels, 'Motility',
            Puncta3DCanvas(parent, middleIdx, treeModels, fulllstate, filePaths, opt)
        )

        viewMenu = QtWidgets.QMenu('View', self)
        viewMenu.addSeparator()
        self._addScrollActions(viewMenu)
        self.menuBar().addMenu(viewMenu)

