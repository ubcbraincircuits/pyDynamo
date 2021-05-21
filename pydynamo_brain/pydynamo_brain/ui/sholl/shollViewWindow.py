from PyQt5 import QtCore,  QtWidgets
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

        self.label = QtWidgets.QLabel('Error Bars are Standard Deviation', self)
        self.label.setAlignment(QtCore.Qt.AlignCenter)


        root = QtWidgets.QWidget(self)
        l = QtWidgets.QVBoxLayout(root)
        l.setContentsMargins(5, 5, 5, 5)
        l.addWidget(self.view)
        l.addWidget(self.label)

        root.setFocus()
        self.setCentralWidget(root)
