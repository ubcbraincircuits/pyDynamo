from PyQt5 import QtCore, QtWidgets
from .shollCanvas import ShollCanvas

# Scrollable list of stacks, showing registration between stack pairs.
class ShollViewWindow(QtWidgets.QMainWindow):
    def __init__(self, parent, fullState, treeModels):
        '''super().__init__(parent, fullState, 'Sholl Analysis',
            ShollCanvas(parent, fullState,)  '''
        super(ShollViewWindow, self).__init__(parent)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowTitle('Sholl')


        self.view = ShollCanvas(self, fullState, treeModels)

        root = QtWidgets.QWidget(self)
        l = QtWidgets.QHBoxLayout(root)
        l.setContentsMargins(0, 0, 0, 0)
        l.addWidget(self.view)
        root.setFocus()
        self.setCentralWidget(root)
