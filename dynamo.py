import sys
import matplotlib
from PyQt5 import QtCore, QtWidgets

matplotlib.use('Qt5Agg')
from mpl_toolkits.mplot3d import Axes3D

from ui import AppWindow

# RUN DYNAMO
qtApp = QtWidgets.QApplication(sys.argv)
uiApp = AppWindow()
uiApp.show()
sys.exit(qtApp.exec_())
