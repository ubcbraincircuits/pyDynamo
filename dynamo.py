import sys
import matplotlib
from PyQt5 import QtCore, QtWidgets

matplotlib.use('Qt5Agg')
from mpl_toolkits.mplot3d import Axes3D

from ui import DynamoWindow

# RUN DYNAMO
qtApp = QtWidgets.QApplication(sys.argv)
dynamoWindow = DynamoWindow()
print ("Exec!")
res = qtApp.exec_()
print ("EXIT!")
sys.exit(res)
