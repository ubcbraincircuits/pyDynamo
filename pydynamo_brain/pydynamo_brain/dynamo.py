import sys
import matplotlib
from PyQt5 import QtCore, QtWidgets

from .ui import DynamoWindow

def runDynamo():
    # Need to configure mpl before importing 3D axes
    matplotlib.use('Qt5Agg')
    from mpl_toolkits.mplot3d import Axes3D

    qtApp = QtWidgets.QApplication(sys.argv)
    dynamoWindow = DynamoWindow(qtApp, sys.argv[1:])
    print ("Exec!")
    res = qtApp.exec_()
    print ("EXIT!")
    sys.exit(res)

# RUN DYNAMO
if __name__ == '__main__':
    runDynamo()
