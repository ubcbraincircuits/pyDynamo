import napari

from PyQt5.QtCore import QRectF
from PyQt5.QtWidgets import QApplication, QWidget, QInputDialog, QLineEdit, QMessageBox

import pydynamo_brain.util as util

from pydynamo_brain.ui.branchToColorMap import BranchToColorMap
from pydynamo_brain.ui.common import createAndShowInfo
from pydynamo_brain.ui.dendrite3DViewWindow import Dendrite3DViewWindow
from pydynamo_brain.ui.helpDialog import showHelpDialog
from pydynamo_brain.ui.registration.idRegisterWindow import IdRegisterWindow
from pydynamo_brain.ui.volume3DWindow import Volume3DWindow

from pydynamo_brain.files import importFromSWC
from pydynamo_brain.model import IdAligner, PointMode, recursiveAdjust
from pydynamo_brain.model.tree.util import findTightAngles

class DendriteCanvasActions():
    COLOR_SENSITIVITY = 10.0 / 256.0

    def __init__(self, windowIndex, fullActions, uiState, dendriteCanvas, imagePath):
        self.windowIndex = windowIndex
        self.fullActions = fullActions
        self.uiState = uiState
        self.canvas = dendriteCanvas
        self.imagePath = imagePath
        self.branchToColorMap = BranchToColorMap()

    def _stackWindow(self):
        return self.canvas.stackWindow

    def updateUIState(self, newUiState):
        self.uiState = newUiState

    def updateWindowIndex(self, windowIndex):
        self.windowIndex = windowIndex

    def zoom(self, logAmount):
        self.canvas.imgView.zoom(logAmount)

    def pan(self, xDelta, yDelta):
        outsideRect = self.canvas.imgView.sceneRect()
        viewBox = self.canvas.imgView.getViewportRect()
        xDeltaPx = util.snapToRange(
            (int)(xDelta * viewBox.width() * 0.1),
            outsideRect.left() - viewBox.left(),
            outsideRect.right() - viewBox.right()
        )
        yDeltaPx = util.snapToRange(
            (int)(yDelta * viewBox.height() * 0.1),
            outsideRect.top() - viewBox.top(),
            outsideRect.bottom() - viewBox.bottom()
        )
        viewBox.translate(xDeltaPx, yDeltaPx)
        viewBox = viewBox.intersected(self.canvas.imgView.sceneRect())
        self.canvas.imgView.moveViewRect(viewBox)

    def changeBrightness(self, lower, upper, reset=False):
        if reset:
            self.uiState.colorLimits = (0, 1)
        else:
            self.uiState.changeBrightness(lower * self.COLOR_SENSITIVITY, upper * self.COLOR_SENSITIVITY)
        self.canvas.redraw()

    def showHotkeys(self):
        showHelpDialog()

    def toggleZProjection(self):
        self.uiState.zProject = not self.uiState.zProject
        self.canvas.redraw()

    def markPoints(self):
        self.uiState.setAllDownstreamPointsMarked(marked=True)
        self.canvas.redraw()

    def unmarkPoints(self):
        self.uiState.setAllDownstreamPointsMarked(marked=False)
        self.canvas.redraw()

    # Perform basic checks and show the result:
    def performChecks(self):
        # TODO: split these out elsewhere if it grows too big.
        thisTree = self.uiState.parent().trees[self.windowIndex]
        badBends = findTightAngles(thisTree)
        print ("Tight angles:")
        for bend in badBends:
            print ("\t%s -> %s -> %s has angle %.2f deg" % (bend[0].id, bend[1].id, bend[2].id, bend[3]))
        if len(badBends) == 0:
            print ("\tNone found!")

        if self.windowIndex > 0:
            lastTree = self.uiState.parent().trees[self.windowIndex - 1]
            print ("Changed branches:")
            changed = False
            for thisP in thisTree.flattenPoints():
                lastP = lastTree.getPointByID(thisP.id)
                if lastP is None:
                    continue
                if thisP.parentBranch is None or lastP.parentBranch is None:
                    continue # roots
                if lastP.parentBranch.id != thisP.parentBranch.id:
                    changed = True
                    print ("\tPoint %s changed from branch %s to branch %s" % (
                        thisP.id, lastP.parentBranch.id, thisP.parentBranch.id
                    ))
            if not changed:
                print ("\tNone found!")


        # TODO: show in message box in UI instead?
        QMessageBox.information(self.canvas.parent(), "Done", "Checks performed - see console for results")

    def launch3DArbor(self):
        stackWindow = self._stackWindow()
        infoBox = createAndShowInfo("Drawing 3D Arbor", stackWindow)
        viewWindow = Dendrite3DViewWindow(stackWindow, self.imagePath, self.uiState._tree)
        infoBox.hide()
        viewWindow.show()

    def launch3DVolume(self):
        stackWindow = self._stackWindow()
        infoBox = createAndShowInfo("Drawing 3D Volume", stackWindow)
        viewWindow = Volume3DWindow(stackWindow, self.uiState)
        infoBox.hide()
        viewWindow.show()

    def importPointsFromLastStack(self, windowIndex):
        if windowIndex == 0:
            print ("Can't import points into the first image, nothing to import from...")
            return
        thisTree = self.uiState.parent().trees[windowIndex]
        lastTree = self.uiState.parent().trees[windowIndex - 1]
        assert thisTree is not None and lastTree is not None
        thisTree.clearAndCopyFrom(lastTree, None) # No id maker, so clone IDs
        self.branchToColorMap.addNewTree(thisTree)

    def importPointsFromSWC(self, windowIndex, filePath):
        thisTree = self.uiState.parent().trees[windowIndex]
        if thisTree is None or thisTree.rootPoint is not None:
            print ("Arbor has points already, please only run on an empty image.")
            return
        newTree = importFromSWC(filePath)
        if newTree is not None:
            thisTree.clearAndCopyFrom(newTree, self.uiState.parent())
            self.branchToColorMap.addNewTree(thisTree)

    def smartRegisterImages(self, windowIndex):
        if windowIndex == 0:
            print ("Can't register the first image, nothing to register it against...")
            return

        stackWindow = self._stackWindow()
        self.fullActions.history.pushState()

        pointNew = self.uiState.currentPoint()
        pointOld = self.uiState.parent().uiStates[windowIndex-1].currentPoint()
        branch = None if pointNew is None else pointNew.parentBranch

        # Default to root if anything is wrong...
        if pointNew is None or pointOld is None or branch is None:
            branch = None
            pointNew = self.uiState.parent().trees[windowIndex].rootPoint
            pointOld = self.uiState.parent().trees[windowIndex-1].rootPoint

        # Un-mark old points
        allSubtreePoints = pointNew.flattenSubtreePoints()
        pointCount = len(allSubtreePoints)
        for p in allSubtreePoints:
            p.manuallyMarked = False

        # Progress bar! Note: array here as it's edited inside the callback.
        pointAt = [0]
        infoBox = createAndShowInfo("Registering", stackWindow)
        self.canvas.stackWindow.statusBar().showMessage(
            "Registering...  %d/%d points processed." % (pointAt[0], pointCount))
        self.canvas.stackWindow.repaint()
        def progressUpdate(pointsProcessed):
            pointAt[0] += pointsProcessed
            self.canvas.stackWindow.statusBar().showMessage(
                "Registering...  %d/%d points processed." % (pointAt[0], pointCount))

        recursiveAdjust(self.uiState.parent(), windowIndex, branch, pointNew, pointOld, progressUpdate)
        self.uiState.showMarked = True
        self.canvas.redraw()
        msg = QMessageBox(QMessageBox.Information, "Registration",
            "Registration complete! Unregistered points marked, press 'h' to toggle showing them.", parent=self.canvas)
        msg.show()
        infoBox.hide()
        self.canvas.stackWindow.statusBar().clearMessage()

    def simpleRegisterImages(self, windowIndex, somaScale=1.01):
        if windowIndex == 0:
            print ("Can't register the first image, nothing to register it against...")
            return

        self.fullActions.history.pushState()

        fullState = self.uiState.parent()
        oldTree = fullState.trees[windowIndex - 1]
        newTree = fullState.trees[windowIndex]

        registrationWindow = IdRegisterWindow(self.canvas.parent(), fullState, oldTree, newTree)
        registrationWindow.showMaximized()

        redrawFunc = lambda: self.canvas.redraw()
        registrationWindow.startRegistration(redrawFunc)

    def startReplaceParent(self):
        self.uiState.pointMode = PointMode.REPARENT
        self.canvas.redraw()

    def stopReplaceParent(self):
        self.uiState.pointMode = PointMode.DEFAULT
        self.canvas.redraw()

    # Cycle selection -> Moving -> Reparenting -> back
    def cyclePointModes(self):
        # POIUY
        currentPoint = self.uiState.currentPoint()
        if currentPoint is not None:
            if self.uiState.isMoving():
                # Moving -> Reparenting
                self.fullActions.cancelMove()
                self.startReplaceParent()
            elif self.uiState.isReparenting():
                # Reparenting -> Selection
                self.stopReplaceParent()
            else:
                # Selection -> Moving
                self.fullActions.beginMove(self.windowIndex, currentPoint)
