import numpy as np
import threading
import time

from PyQt5 import QtCore, QtWidgets
from tqdm import tqdm

from pydynamo_brain.model import IdAligner
from pydynamo_brain.ui.baseMatplotlibCanvas import BaseMatplotlibCanvas

# Configuration: These can be played around with if you know what you're doing.

# Max distance from previous paired points to new paired points.
MAX_SKIP = 3 # Caution: bigger results in *a lot* slower computation.

# For points at two times this distance apart, we prefer to leave them unmatched as they're too far.
UNMATCHED_PENALTY_UM = 10

# UI Colors
GREY     = (0.75, 0.75, 0.75, 0.75)
GREEN    = (0.00, 1.00, 0.00)
RED      = (1.00, 0.00, 0.00)
BLUE     = (0.00, 0.00, 1.00)
PURPLE   = (1.00, 0.00, 1.00)

class IdRegisterThread(QtCore.QThread):
    signal = QtCore.pyqtSignal('PyQt_PyObject')

    def __init__(self, treeA, treeB):
        QtCore.QThread.__init__(self)
        self.treeA = treeA
        self.treeB = treeB
        self.cancelled = False

    # Runs in another thread:
    def run(self):
        # TODO: custom arguments?
        aligner = IdAligner(self.treeA, self.treeB, maxSkip=MAX_SKIP, unmatchedPenalty=UNMATCHED_PENALTY_UM)
        alignment = {}

        maxCount = aligner.maxCallCount()
        self.signal.emit( (0, maxCount) )

        with tqdm(total=maxCount, desc='Aligning...') as consoleProgress:
            def _updateFunc():
                self.signal.emit( (1, None) )
                consoleProgress.update(1)
                self.cancelled = self.cancelled or self.isInterruptionRequested()
                return self.cancelled

            alignment = aligner.performAlignment(_updateFunc)
            if not self.cancelled:
                self.signal.emit( (2, alignment) )

class IdRegisterPair(BaseMatplotlibCanvas):
    def __init__(self, parent, treeA, treeB, isAfter, *args, **kwargs):
        self.treeA = treeA
        self.treeB = treeB
        self.isAfter = isAfter
        super(IdRegisterPair, self).__init__(*args, in3D=True, subplots=2, **kwargs)
        self.fig.canvas.mpl_connect('motion_notify_event', self.handleMove)
        self.fig.subplots_adjust(top=0.95, bottom=0.05, right=0.95, left=0.05, wspace=0.05, hspace=0.05)

    def drawPointsOneColor(self, ax, treeModel, points, color, delta=(0, 0, 0), **kwargs):
        if len(points) > 0:
            x, y, z = treeModel.worldCoordPoints(points)
            x = [v + delta[0] for v in x]
            y = [v + delta[1] for v in y]
            z = [v + delta[2] for v in z]
            ax.scatter(x, y, z, c=[color], **kwargs)

    def drawWithMarked(self, ax, tree, idsToColorMaps):
        # Draw lines for each branch:
        for branch in tree.branches:
            if branch.parentPoint is None:
                continue
            points = [branch.parentPoint] + branch.points
            x, y, z = tree.worldCoordPoints(points)
            ax.plot(x, y, z, c=GREY, lw=1) # TODO - draw axon differently?

        # Split points by keep/new status:
        somaColor = GREY
        colorPoints = [[] for idsForColor in idsToColorMaps]
        greyPoints = []
        for p in tree.flattenPoints():
            added = False
            for c, idsForColor in enumerate(idsToColorMaps):
                if p.id in idsForColor[0]:
                    added = True
                    if p.isRoot():
                        somaColor = idsForColor[1]
                    else:
                        colorPoints[c].append(p)
            if not added:
                greyPoints.append(p)

        # Draw the points by keep/remove:
        for (points, colorMaps) in zip(colorPoints, idsToColorMaps):
            self.drawPointsOneColor(ax, tree, points, colorMaps[1], s=4)
        self.drawPointsOneColor(ax, tree, greyPoints, GREY, s=4)
        self.drawPointsOneColor(ax, tree, [tree.rootPoint], somaColor, s=350) # Big soma

    def compute_initial_figure(self):
        for ax in self.axes:
            ax.cla()
            # TODO: reenable once matplotlib supports it again
            #ax.set_aspect('equal')

        if not self.isAfter:
            idsA = set([p.id for p in self.treeA.flattenPoints()])
            idsB = set([p.id for p in self.treeB.flattenPoints()])

            # Points in A and not B = Removed (red)
            removedPoints = idsA - idsB
            self.drawWithMarked(self.axes[0], self.treeA, [
                (idsA - idsB, RED)
            ])

            # Points in B and not A = Added (green)
            addedPoints = idsB - idsA
            self.drawWithMarked(self.axes[1], self.treeB, [
                (addedPoints, GREEN)
            ])

    def updateWithResults(self, results):
        if self.isAfter:
            flatA = self.treeA.flattenPoints()
            flatB = self.treeB.flattenPoints()
            idsA = set([p.id for p in flatA])
            idsB = set([p.id for p in flatB])

            idsARemapped = set(results.values())
            idsBRemapped = set(results.keys())

            # Points in A and not B = removed (red)
            # Points in A and B and remapped: purple
            removedPoints = (idsA - idsB) - idsARemapped
            self.drawWithMarked(self.axes[0], self.treeA, [
                (removedPoints, RED),
                (idsARemapped, PURPLE),
            ])

            # Points in B and not A = added (green)
            # Points in B and A and remapped: purple
            addedPoints = (idsB - idsA) - idsBRemapped
            self.drawWithMarked(self.axes[1], self.treeB, [
                (addedPoints, GREEN),
                (idsBRemapped, PURPLE)
            ])

            xA, yA, zA = self.treeA.worldCoordPoints(flatA)
            xB, yB, zB = self.treeB.worldCoordPoints(flatB)
            xlim = (np.min(xA + xB), np.max(xA + xB))
            ylim = (np.min(yA + yB), np.max(yA + yB))
            zlim = (np.min(zA + zB), np.max(zA + zB))
            for ax in self.axes:
                ax.set_xlim3d(xlim, emit=False)
                ax.set_ylim3d(ylim, emit=False)
                ax.set_zlim3d(zlim, emit=False)

            self.draw()

    def handleMove(self, event):
        eAx = event.inaxes
        if event.inaxes in self.axes:
            for ax in self.axes:
                if ax == event.inaxes:
                    continue
                ax.view_init(elev=eAx.elev, azim=eAx.azim)
                ax.set_xlim3d(event.inaxes.get_xlim3d(), emit=False)
                ax.set_ylim3d(event.inaxes.get_ylim3d(), emit=False)
                ax.set_zlim3d(event.inaxes.get_zlim3d(), emit=False)


class IdRegisterWindow(QtWidgets.QMainWindow):
    """Window that performs an id-only registration, and shows the results."""

    def __init__(self, parent, fullState, oldTree, newTree):
        QtWidgets.QMainWindow.__init__(self, parent)
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.CustomizeWindowHint | QtCore.Qt.WindowStaysOnTopHint)
        self.setWindowTitle("ID Registration")

        self.root = QtWidgets.QWidget(self)
        self.fullState = fullState
        self.oldTree = oldTree
        self.newTree = newTree
        self.backgroundThread = None
        self.idRemapResults = None
        self.successFunc = None

        l = QtWidgets.QGridLayout()
        at = 0

        l.addWidget(QtWidgets.QLabel("Added/Removed before:"), at, 0); at += 1
        self.beforeView = IdRegisterPair(self, oldTree, newTree, False)
        l.addWidget(self.beforeView, at, 0); at += 1

        l.addWidget(QtWidgets.QLabel("Progress (rough):"), at, 0); at += 1
        self.progress = QtWidgets.QProgressBar(self)
        l.addWidget(self.progress, at, 0); at += 1 #, alignment=Qt.AlignCenter)

        l.addWidget(QtWidgets.QLabel("Added/Removed after: (will appear when done)"), at, 0); at += 1
        self.afterView = IdRegisterPair(self, oldTree, newTree, True)
        l.addWidget(self.afterView, at, 0); at += 1

        self.applyButton = QtWidgets.QPushButton("Apply", self)
        self.cancelButton = QtWidgets.QPushButton("Cancel", self)
        l.addWidget(self.applyButton, at, 0); at += 1
        l.addWidget(self.cancelButton, at, 0); at += 1

        self.applyButton.clicked.connect(self.applyChanges)
        self.cancelButton.clicked.connect(self.cancelRun)

        self.root.setLayout(l)
        self.applyButton.setEnabled(False)
        self.setCentralWidget(self.root)

    def startRegistration(self, successFunc=None):
        self.successFunc = successFunc
        self.backgroundThread = IdRegisterThread(self.oldTree, self.newTree)
        self.backgroundThread.signal.connect(self.handleCallback)
        self.backgroundThread.start()

    def handleCallback(self, bundle):
        if bundle[0] == 0:
            self.progress.setMaximum(bundle[1])
        elif bundle[0] == 1:
            self.progress.setValue(self.progress.value() + 1)
        elif bundle[0] == 2:
            time.sleep(1)
            self.progress.setValue(self.progress.maximum())
            self.idRemapResults = bundle[1]
            print ("Remaps found:")
            for mapFrom, mapTo in self.idRemapResults.items():
                print ("    %s -> %s" % (mapFrom, mapTo))
            self.afterView.updateWithResults(self.idRemapResults)
            self.applyButton.setEnabled(True)
            self.backgroundThread.requestInterruption()
            self.backgroundThread.wait()
            self.backgroundThread = None
        else:
            print ("Hmm...")
            print (bundle)

    # Apply the suggested ID remappings:
    def applyChanges(self):
        if self.idRemapResults is None:
            return

        # Need to look up all first, to make sure none get remapped during the process
        cachedPoints = {}
        for mapFrom, mapTo in self.idRemapResults.items():
            cachedPoints[mapFrom] = self.newTree.getPointByID(mapFrom)
        for mapFrom, mapTo in self.idRemapResults.items():
            self.fullState.setPointIDWithoutCollision(
                self.newTree, cachedPoints[mapFrom], mapTo)

        msg = "%d ID remaps performed." % len(self.idRemapResults)
        QtWidgets.QMessageBox.information(self, "Remapped", msg)

        if self.successFunc is not None:
            self.successFunc()
        self.close()

    # Ignore remappings, and stop the matching if it's still going on.
    def cancelRun(self):
        if self.backgroundThread is not None:
            self.backgroundThread.requestInterruption()
            self.backgroundThread.wait()
            self.backgroundThread = None
        self.close()
