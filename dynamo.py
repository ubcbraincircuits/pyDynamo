import sys
import matplotlib
from PyQt5 import QtCore, QtWidgets

matplotlib.use('Qt5Agg')
from mpl_toolkits.mplot3d import Axes3D

import files
from ui import AppWindow
from model import Tree, UIState

imageVolume = files.tiffRead('data/Live4-1-2015_09-16-03.tif')
treeModel = Tree()
uiState = UIState(tree=treeModel)

# RUN DYNAMO
qtApp = QtWidgets.QApplication(sys.argv)
uiApp = AppWindow(imageVolume, treeModel, uiState)
uiApp.show()
sys.exit(qtApp.exec_())
