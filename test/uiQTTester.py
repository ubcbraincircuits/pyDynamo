
# embedding_in_qt5.py --- Simple Qt5 application embedding matplotlib canvases
#
# Copyright (C) 2005 Florent Rougon
#               2006 Darren Dale
#               2015 Jens H Nielsen
#
# This file is an example program for matplotlib. It may be used and
# modified with no restriction; raw copies as well as modified versions
# may be distributed without limitation.


from __future__ import unicode_literals
import sys
import os
import random
import matplotlib
import numpy as np
# Make sure that we are using QT5
matplotlib.use('Qt5Agg')
from PyQt5 import QtCore, QtWidgets

from numpy import arange, sin, pi
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D

progname = os.path.basename(sys.argv[0])
progversion = "0.1"

from calc import absorient
import files
import util

n = 5
POINTS = np.random.rand(n, 3)
ROTPOINTS = absorient.hackRotate(POINTS)


class MyMplCanvas(FigureCanvas):
    # Ultimately, this is a QWidget (as well as a FigureCanvasAgg, etc.).

    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111, projection='3d')
        self.compute_initial_figure()
        FigureCanvas.__init__(self, fig)
        self.axes.mouse_init()
        self.setParent(parent)

        FigureCanvas.setSizePolicy(self,
                                   QtWidgets.QSizePolicy.Expanding,
                                   QtWidgets.QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)

    def compute_initial_figure(self):
        pass


class MyStaticMplCanvas(MyMplCanvas):
    def __init__(self, data, *args, **kwargs):
        self.data = data
        super(MyStaticMplCanvas, self).__init__(*args, **kwargs)

    def compute_initial_figure(self):
        s = self.data.shape
        """
        idx = np.indices(np.array(self.data.shape) + 1).astype(float)
        x, y, z = idx[0], idx[1], idx[2]

        fill = np.ones(s)

        # fCol = np.ones((s[0], s[1], s[2], 1))
        fCol = np.ndarray(shape=s, dtype=str)
        for i in range(s[0]):
            for j in range(s[1]):
                for k in range(s[2]):
                    # asCol = np.array([0, 0, 255, self.data[i,j,k]])
                    red, green, blue, alpha = 127, 127, 127, 127 # int(self.data[i,j,k] * 255)
                    asCol = '#{a:02x}{r:02x}{g:02x}{b:02x}'.format(r=red,g=green,b=blue,a=alpha)
                    fCol[i,j,k] = asCol
        self.axes.voxels(x, y, z, fill, facecolors=fCol)
        """
        # n_voxels = np.zeros((4, 3, 4), dtype=bool)
        # n_voxels[0, 0, :] = True
        # n_voxels[-1, 0, :] = True
        # n_voxels[1, 0, 2] = True
        # n_voxels[2, 0, 1] = True

        fCol = np.ndarray(shape=s, dtype='<U9')
        for i in range(s[0]):
            for j in range(s[1]):
                for k in range(s[2]):
                    # asCol = np.array([0, 0, 255, self.data[i,j,k]])
                    red, green, blue, alpha = 0, 0, 0, int(self.data[i,j,k] * 255)
                    asCol = '#{r:02x}{g:02x}{b:02x}{a:02x}'.format(r=red,g=green,b=blue,a=alpha)
                    fCol[i,j,k] = asCol

        # facecolors = np.where(n_voxels, '#FFD65DC0', '#7A88CCC0')
        # edgecolors = np.where(n_voxels, '#BFAB6E', '#7D84A6')
        filled = np.ones(s)
        filled_2 = self.explode(filled)
        fcolors_2 = self.explode(fCol)
        ecolors_2 = fcolors_2 # self.explode(edgecolors)

        x, y, z = np.indices(np.array(filled_2.shape) + 1).astype(float) // 2
        x[0::2, :, :] += 0.05
        y[:, 0::2, :] += 0.05
        z[:, :, 0::2] += 0.05
        x[1::2, :, :] += 0.95
        y[:, 1::2, :] += 0.95
        z[:, :, 1::2] += 0.95

        self.axes.voxels(x, y, z, filled_2, facecolors=fcolors_2, edgecolors=ecolors_2)

    def updateData(self, data):
        self.data = data
        self.axes.cla()
        self.axes.scatter(data[:, 0], data[:, 1], data[:, 2])
        self.draw()

    def mousePressEvent(self, event):
        print ("Clicked: (%d %d)" % (event.globalX(), event.globalY()))
        super(MyStaticMplCanvas, self).mousePressEvent(event)

    def explode(self, data):
        size = np.array(data.shape)*2
        data_e = np.zeros(size - 1, dtype=data.dtype)
        data_e[::2, ::2, ::2] = data
        return data_e



class ApplicationWindow(QtWidgets.QMainWindow):
    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowTitle("application main window")

        self.file_menu = QtWidgets.QMenu('&File', self)
        self.file_menu.addAction('&Quit', self.fileQuit,
                                 QtCore.Qt.CTRL + QtCore.Qt.Key_Q)
        self.menuBar().addMenu(self.file_menu)

        self.help_menu = QtWidgets.QMenu('&Help', self)
        self.menuBar().addSeparator()
        self.menuBar().addMenu(self.help_menu)

        self.help_menu.addAction('&About', self.about)

        self.main_widget = QtWidgets.QWidget(self)

        l = QtWidgets.QVBoxLayout(self.main_widget)

        hackVolume = util.tiffRead('data/Live4-1-2015_09-16-03.tif')
        hackVolume = np.array(hackVolume[:int(len(hackVolume) / 2)])
        hackVolume = hackVolume[::2, ::16, ::16]
        hackVolume = (hackVolume - hackVolume.min()) / (hackVolume.max() - hackVolume.min())
        print("VOL")
        print(hackVolume.shape)


        self.scatter3d = MyStaticMplCanvas(hackVolume, self.main_widget, width=5, height=4, dpi=100)
        # self.scatter3dRot = MyStaticMplCanvas(ROTPOINTS, self.main_widget, width=5, height=4, dpi=100)
        # dc = MyDynamicMplCanvas(self.main_widget, width=5, height=4, dpi=100)
        l.addWidget(self.scatter3d)
        # l.addWidget(self.scatter3dRot)

        self.main_widget.setFocus()
        self.setCentralWidget(self.main_widget)

        self.statusBar().showMessage("All hail matplotlib!", 2000)

    def fileQuit(self):
        self.close()

    def closeEvent(self, ce):
        self.fileQuit()

    def about(self):
        QtWidgets.QMessageBox.about(self, "About", "Fill in stuff here?")

    def keyPressEvent(self, event):
        if (event.key() == 32):
            newP = np.random.rand(n, 3)
            newPRot = absorient.hackRotate(newP)
            self.scatter3d.updateData(newP)
            # self.scatter3dRot.updateData(newPRot)

qApp = QtWidgets.QApplication(sys.argv)

aw = ApplicationWindow()
aw.setWindowTitle("%s" % progname)
aw.show()
sys.exit(qApp.exec_())
#qApp.exec_()
