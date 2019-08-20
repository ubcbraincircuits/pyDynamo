from PyQt5 import QtCore, QtWidgets

from pydynamo_brain.ui.scrollableStacksWindow import ScrollableStacksWindow

from .motility3DCanvas import Motility3DCanvas

# Scrollable list of stacks, showing motility in the stack, in 2D or 3D.
class Motility3DViewWindow(ScrollableStacksWindow):
    def __init__(self, parent, middleIdx, treeModels, is2D, filePaths, opt):
        super().__init__(parent, treeModels, 'Motility',
            Motility3DCanvas(parent, middleIdx, treeModels, is2D, filePaths, opt)
        )

        viewMenu = QtWidgets.QMenu('View', self)
        viewMenu.addAction('Show 3D', self.show3D, QtCore.Qt.Key_3)
        viewMenu.addAction('Show 2D Dendrograms', self.show2D, QtCore.Qt.Key_2)
        viewMenu.addSeparator()
        self._addScrollActions(viewMenu)
        self.menuBar().addMenu(viewMenu)

    def show3D(self):
        self.view.set3D(True)

    def show2D(self):
        self.view.set3D(False)
