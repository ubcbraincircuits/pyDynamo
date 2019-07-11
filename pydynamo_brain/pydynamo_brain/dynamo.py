import sys
import matplotlib
from PyQt5 import QtCore, QtWidgets

matplotlib.use('Qt5Agg')
from mpl_toolkits.mplot3d import Axes3D
from .ui import DynamoWindow

def runDynamo():
    qtApp = QtWidgets.QApplication(sys.argv)
    dynamoWindow = DynamoWindow(qtApp, sys.argv[1:])
    print ("Exec!")
    res = qtApp.exec_()
    print ("EXIT!")
    sys.exit(res)

# RUN DYNAMO
if __name__ == '__main__':
    runDynamo()
