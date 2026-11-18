import numpy as np

from PyQt5 import QtCore, QtWidgets
from tqdm import tqdm

from pydynamo_brain.model import IdAligner
from pydynamo_brain.ui.baseMatplotlibCanvas import BaseMatplotlibCanvas
from pydynamo_brain.ui.branchToColorMap import BranchToColorMap
from pydynamo_brain.ui.registration.heuristicIdAligner import (
    HeuristicIdAligner,
    sync_target_branches_to_reference,
)

# Configuration: Legacy tree-edit DP defaults
MAX_SKIP = 3  # Caution: bigger results in *a lot* slower computation in legacy DP.
UNMATCHED_PENALTY_UM = 10

# Heuristic v2 defaults
DEFAULT_BP_THRESH_UM = 5.0
DEFAULT_PT_THRESH_UM = 5.0

# UI Colors
GREY   = (0.75, 0.75, 0.75, 0.75)
GREEN  = (0.00, 1.00, 0.00)
RED    = (1.00, 0.00, 0.00)
BLUE   = (0.00, 0.00, 1.00)
PURPLE = (1.00, 0.00, 1.00)


class IdRegisterThread(QtCore.QThread):
    signal = QtCore.pyqtSignal('PyQt_PyObject')

    def __init__(
        self,
        treeA,
        treeB,
        useHeuristic=True,
        autoScale=True,
        branchPointThreshold=DEFAULT_BP_THRESH_UM,
        pointThreshold=DEFAULT_PT_THRESH_UM,
        maxSkip=MAX_SKIP,
        unmatchedPenalty=UNMATCHED_PENALTY_UM,
    ):
        QtCore.QThread.__init__(self)
        self.treeA = treeA
        self.treeB = treeB
        self.useHeuristic = useHeuristic
        self.autoScale = autoScale
        self.branchPointThreshold = branchPointThreshold
        self.pointThreshold = pointThreshold
        self.maxSkip = maxSkip
        self.unmatchedPenalty = unmatchedPenalty
        self.cancelled = False

    def run(self):
        if self.useHeuristic:
            aligner = HeuristicIdAligner(
                self.treeA,
                self.treeB,
                branchPointThreshold=self.branchPointThreshold,
                pointThreshold=self.pointThreshold,
                maxSkip=self.maxSkip,
                autoScale=self.autoScale,
            )
            maxCount = aligner.maxCallCount()
            self.signal.emit((0, maxCount))

            def _updateFunc():
                self.signal.emit((1, None))
                self.cancelled = self.cancelled or self.isInterruptionRequested()
                return self.cancelled

            details = aligner.performAlignmentDetailed(_updateFunc)
            if not self.cancelled:
                self.signal.emit((2, details.remap, details))
        else:
            aligner = IdAligner(
                self.treeA,
                self.treeB,
                maxSkip=self.maxSkip,
                unmatchedPenalty=self.unmatchedPenalty,
            )
            maxCount = aligner.maxCallCount()
            self.signal.emit((0, maxCount))

            with tqdm(total=maxCount, desc='Aligning...') as consoleProgress:
                def _updateFunc():
                    self.signal.emit((1, None))
                    consoleProgress.update(1)
                    self.cancelled = self.cancelled or self.isInterruptionRequested()
                    return self.cancelled

                alignment = aligner.performAlignment(_updateFunc)
                if not self.cancelled:
                    self.signal.emit((2, alignment, None))


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
            ax.plot(x, y, z, c=GREY, lw=1)

        # Split points by keep/new status:
        somaColor = GREY
        colorPoints = [[] for _ in idsToColorMaps]
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
        for points, colorMaps in zip(colorPoints, idsToColorMaps):
            self.drawPointsOneColor(ax, tree, points, colorMaps[1], s=4)
        self.drawPointsOneColor(ax, tree, greyPoints, GREY, s=4)
        self.drawPointsOneColor(ax, tree, [tree.rootPoint], somaColor, s=350)  # Big soma

    def compute_initial_figure(self):
        for ax in self.axes:
            ax.cla()

        if not self.isAfter:
            idsA = set([p.id for p in self.treeA.flattenPoints()])
            idsB = set([p.id for p in self.treeB.flattenPoints()])

            # Points in A and not B = Removed (red)
            removedPoints = idsA - idsB
            self.drawWithMarked(self.axes[0], self.treeA, [
                (removedPoints, RED)
            ])

            # Points in B and not A = Added (green)
            addedPoints = idsB - idsA
            self.drawWithMarked(self.axes[1], self.treeB, [
                (addedPoints, GREEN)
            ])

    def updateWithResults(self, results, details=None):
        if self.isAfter:
            for ax in self.axes:
                ax.cla()

            flatA = self.treeA.flattenPoints()
            flatB = self.treeB.flattenPoints()
            idsA = set([p.id for p in flatA])
            idsB = set([p.id for p in flatB])

            idsARemapped = set(results.values())
            idsBRemapped = set(results.keys())

            if details is not None:
                removedPoints = set(details.removed_points_A)
                addedPoints = set(details.added_points_B)
            else:
                removedPoints = (idsA - idsB) - idsARemapped
                addedPoints = (idsB - idsA) - idsBRemapped

            self.drawWithMarked(self.axes[0], self.treeA, [
                (removedPoints, RED),
                (idsARemapped, PURPLE),
            ])

            self.drawWithMarked(self.axes[1], self.treeB, [
                (addedPoints, GREEN),
                (idsBRemapped, PURPLE),
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
    """Window that performs an ID-only registration and shows 3D before/after results."""

    def __init__(self, parent, fullState, oldTree, newTree, useHeuristic=True):
        QtWidgets.QMainWindow.__init__(self, parent)
        self.setWindowFlags(
            self.windowFlags() | QtCore.Qt.CustomizeWindowHint | QtCore.Qt.WindowStaysOnTopHint
        )
        self.setWindowTitle("ID Registration")

        self.root = QtWidgets.QWidget(self)
        self.fullState = fullState
        self.oldTree = oldTree
        self.newTree = newTree
        self.backgroundThread = None
        self.idRemapResults = None
        self.heuristicDetails = None
        self.successFunc = None

        l = QtWidgets.QGridLayout()
        at = 0

        # Method & parameter controls
        controlsLayout = QtWidgets.QHBoxLayout()
        controlsLayout.addWidget(QtWidgets.QLabel("Method:"))
        self.methodCombo = QtWidgets.QComboBox(self)
        self.methodCombo.addItems(["Heuristic (Fast)", "Legacy Tree-Edit DP (Slow)"])
        self.methodCombo.setCurrentIndex(0 if useHeuristic else 1)
        controlsLayout.addWidget(self.methodCombo)

        self.autoScaleCheck = QtWidgets.QCheckBox("Auto-scale thresholds", self)
        self.autoScaleCheck.setChecked(True)
        controlsLayout.addWidget(self.autoScaleCheck)

        controlsLayout.addWidget(QtWidgets.QLabel("Branch-pt (µm):"))
        self.bpThreshSpin = QtWidgets.QDoubleSpinBox(self)
        self.bpThreshSpin.setRange(0.5, 50.0)
        self.bpThreshSpin.setSingleStep(0.5)
        self.bpThreshSpin.setDecimals(1)
        self.bpThreshSpin.setValue(DEFAULT_BP_THRESH_UM)
        controlsLayout.addWidget(self.bpThreshSpin)

        controlsLayout.addWidget(QtWidgets.QLabel("Point (µm):"))
        self.ptThreshSpin = QtWidgets.QDoubleSpinBox(self)
        self.ptThreshSpin.setRange(0.5, 50.0)
        self.ptThreshSpin.setSingleStep(0.5)
        self.ptThreshSpin.setDecimals(1)
        self.ptThreshSpin.setValue(DEFAULT_PT_THRESH_UM)
        controlsLayout.addWidget(self.ptThreshSpin)

        controlsLayout.addWidget(QtWidgets.QLabel("Max skip:"))
        self.maxSkipSpin = QtWidgets.QSpinBox(self)
        self.maxSkipSpin.setRange(1, 6)
        self.maxSkipSpin.setValue(MAX_SKIP)
        controlsLayout.addWidget(self.maxSkipSpin)

        self.syncBranchesCheck = QtWidgets.QCheckBox("Sync branch continuations && IDs", self)
        self.syncBranchesCheck.setChecked(useHeuristic)
        controlsLayout.addWidget(self.syncBranchesCheck)

        self.rerunButton = QtWidgets.QPushButton("Re-run", self)
        controlsLayout.addWidget(self.rerunButton)
        controlsLayout.addStretch(1)

        l.addLayout(controlsLayout, at, 0)
        at += 1

        l.addWidget(QtWidgets.QLabel("Added/Removed before:"), at, 0)
        at += 1
        self.beforeView = IdRegisterPair(self, oldTree, newTree, False)
        l.addWidget(self.beforeView, at, 0)
        at += 1

        l.addWidget(QtWidgets.QLabel("Progress:"), at, 0)
        at += 1
        self.progress = QtWidgets.QProgressBar(self)
        l.addWidget(self.progress, at, 0)
        at += 1

        self.afterLabel = QtWidgets.QLabel("Added/Removed after: (running...)", self)
        l.addWidget(self.afterLabel, at, 0)
        at += 1
        self.afterView = IdRegisterPair(self, oldTree, newTree, True)
        l.addWidget(self.afterView, at, 0)
        at += 1

        buttonLayout = QtWidgets.QHBoxLayout()
        self.applyButton = QtWidgets.QPushButton("Apply", self)
        self.cancelButton = QtWidgets.QPushButton("Cancel", self)
        buttonLayout.addWidget(self.applyButton)
        buttonLayout.addWidget(self.cancelButton)
        l.addLayout(buttonLayout, at, 0)
        at += 1

        self.methodCombo.currentIndexChanged.connect(self._onMethodChanged)
        self.autoScaleCheck.toggled.connect(self._updateControlStates)
        self.rerunButton.clicked.connect(self.rerunRegistration)
        self.applyButton.clicked.connect(self.applyChanges)
        self.cancelButton.clicked.connect(self.cancelRun)

        self._updateControlStates()
        self.root.setLayout(l)
        self.applyButton.setEnabled(False)
        self.setCentralWidget(self.root)

    def _isHeuristicSelected(self):
        return self.methodCombo.currentIndex() == 0

    def _onMethodChanged(self):
        self.syncBranchesCheck.setChecked(self._isHeuristicSelected())
        self._updateControlStates()

    def _updateControlStates(self):
        isHeuristic = self._isHeuristicSelected()
        manualThresh = isHeuristic and not self.autoScaleCheck.isChecked()
        self.autoScaleCheck.setEnabled(isHeuristic)
        self.bpThreshSpin.setEnabled(manualThresh)
        self.ptThreshSpin.setEnabled(manualThresh)
        self.setWindowTitle(
            "ID Registration — Heuristic (Fast)"
            if isHeuristic
            else "ID Registration — Legacy Tree-Edit DP"
        )

    def _stopBackgroundThread(self):
        if self.backgroundThread is not None:
            self.backgroundThread.requestInterruption()
            self.backgroundThread.wait()
            self.backgroundThread = None

    def startRegistration(self, successFunc=None):
        if successFunc is not None:
            self.successFunc = successFunc
        self._stopBackgroundThread()
        self.idRemapResults = None
        self.heuristicDetails = None
        self.applyButton.setEnabled(False)
        self.progress.setValue(0)
        self.afterLabel.setText("Added/Removed after: (running...)")

        self.backgroundThread = IdRegisterThread(
            self.oldTree,
            self.newTree,
            useHeuristic=self._isHeuristicSelected(),
            autoScale=self.autoScaleCheck.isChecked(),
            branchPointThreshold=self.bpThreshSpin.value(),
            pointThreshold=self.ptThreshSpin.value(),
            maxSkip=self.maxSkipSpin.value(),
        )
        self.backgroundThread.signal.connect(self.handleCallback)
        self.backgroundThread.start()

    def rerunRegistration(self):
        self.startRegistration()

    def handleCallback(self, bundle):
        if bundle[0] == 0:
            self.progress.setMaximum(max(1, bundle[1]))
            self.progress.setValue(0)
        elif bundle[0] == 1:
            self.progress.setValue(min(self.progress.maximum(), self.progress.value() + 1))
        elif bundle[0] == 2:
            self.progress.setValue(self.progress.maximum())
            self.idRemapResults = bundle[1]
            self.heuristicDetails = bundle[2] if len(bundle) > 2 else None

            nRemaps = len(self.idRemapResults)
            if self.heuristicDetails is not None:
                d = self.heuristicDetails
                summary = (
                    "Added/Removed after — %d matched (%d remapped, %d branch pts), "
                    "+%d added, -%d removed in %.0f ms (BP=%.1f µm, Pt=%.1f µm)"
                    % (
                        len(d.matched_pairs),
                        nRemaps,
                        len(d.matched_branch_points),
                        len(d.added_points_B),
                        len(d.removed_points_A),
                        d.elapsed_ms,
                        d.effective_bp_thresh_um,
                        d.effective_point_thresh_um,
                    )
                )
                print(summary)
                self.afterLabel.setText(summary)
            else:
                summary = "Added/Removed after — %d ID remaps found" % nRemaps
                print(summary)
                self.afterLabel.setText(summary)

            for idx, (mapFrom, mapTo) in enumerate(self.idRemapResults.items()):
                if idx < 25:
                    print("    %s -> %s" % (mapFrom, mapTo))
                elif idx == 25:
                    print("    ... (%d total remaps)" % nRemaps)
                    break

            self.afterView.updateWithResults(self.idRemapResults, self.heuristicDetails)
            self.applyButton.setEnabled(True)
            self._stopBackgroundThread()
        else:
            print("Unexpected callback bundle:", bundle)

    def applyChanges(self):
        if self.idRemapResults is None:
            return

        # Look up target point references first so intermediate renames cannot collide
        cachedPoints = {
            mapFrom: self.newTree.getPointByID(mapFrom)
            for mapFrom in self.idRemapResults
        }
        unmatchedTargetPoints = (
            [self.newTree.getPointByID(uid) for uid in self.heuristicDetails.added_points_B]
            if self.heuristicDetails is not None
            else []
        )

        nApplied = 0
        for mapFrom, mapTo in self.idRemapResults.items():
            pt = cachedPoints.get(mapFrom)
            if pt is not None:
                self.fullState.setPointIDWithoutCollision(self.newTree, pt, mapTo)
                nApplied += 1

        # Ensure unmatched new points do not retain stale IDs shared with oldTree
        if unmatchedTargetPoints:
            oldIds = {p.id for p in self.oldTree.flattenPoints()}
            for pt in unmatchedTargetPoints:
                if pt is not None and pt.id in oldIds:
                    pt.id = self.fullState.nextPointID()

        if self.syncBranchesCheck.isChecked():
            sync_target_branches_to_reference(self.fullState, self.oldTree, self.newTree)
            BranchToColorMap().initFromFullState(self.fullState)

        msg = "%d ID remaps performed." % nApplied
        QtWidgets.QMessageBox.information(self, "Remapped", msg)

        if self.successFunc is not None:
            self.successFunc()
        self.close()

    def cancelRun(self):
        self._stopBackgroundThread()
        self.close()

    def closeEvent(self, event):
        self._stopBackgroundThread()
        super(IdRegisterWindow, self).closeEvent(event)
