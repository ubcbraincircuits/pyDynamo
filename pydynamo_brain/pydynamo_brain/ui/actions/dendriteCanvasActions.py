from PyQt5.QtCore import QRectF
from PyQt5.QtWidgets import QApplication, QWidget, QInputDialog, QLineEdit, QMessageBox

import pydynamo_brain.util as util
from pydynamo_brain.ui.dendrite3DViewWindow import Dendrite3DViewWindow
from pydynamo_brain.ui.volume3DWindow import Volume3DWindow
from pydynamo_brain.ui.helpDialog import showHelpDialog

from pydynamo_brain.files import importFromSWC
from pydynamo_brain.model import recursiveAdjust

class DendriteCanvasActions():
    COLOR_SENSITIVITY = 10.0 / 256.0

    def __init__(self, windowIndex, fullActions, uiState, dendriteCanvas, imagePath):
        self.windowIndex = windowIndex
        self.fullActions = fullActions
        self.uiState = uiState
        self.canvas = dendriteCanvas
        self.imagePath = imagePath

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

    def launch3DArbor(self):
        viewWindow = Dendrite3DViewWindow(self.canvas.parent(), self.imagePath, self.uiState._tree)
        viewWindow.show()

    def launch3DVolume(self):
        viewWindow = Volume3DWindow(self.canvas.parent(), self.uiState, applyColorLimits=True)
        viewWindow.show()

    def importPointsFromLastStack(self, windowIndex):
        if windowIndex == 0:
            print ("Can't import points into the first image, nothing to import from...")
            return
        thisTree = self.uiState.parent().trees[windowIndex]
        lastTree = self.uiState.parent().trees[windowIndex - 1]
        assert thisTree is not None and lastTree is not None
        thisTree.clearAndCopyFrom(lastTree, None) # No id maker, so clone IDs

    def importPointsFromSWC(self, windowIndex, filePath):
        thisTree = self.uiState.parent().trees[windowIndex]
        if thisTree is None or thisTree.rootPoint is not None:
            print ("Arbor has points already, please only run on an empty image.")
            return
        newTree = importFromSWC(filePath)
        if newTree is not None:
            thisTree.clearAndCopyFrom(newTree, self.uiState.parent())

    def smartRegisterImages(self, windowIndex):
        if windowIndex == 0:
            print ("Can't register the first image, nothing to register it against...")
            return
        self.fullActions.history.pushState()

        pointNew = self.uiState.currentPoint()
        pointOld = self.uiState.parent().uiStates[windowIndex-1].currentPoint()
        branch = None if pointNew is None else pointNew.parentBranch

        # Default to root if anything is wrong...
        if pointNew is None or pointOld is None or branch is None:
            branch = None
            pointNew = self.uiState.parent().trees[windowIndex].rootPoint
            pointOld = self.uiState.parent().trees[windowIndex-1].rootPoint

        # Un-hilight old points
        allSubtreePoints = pointNew.flattenSubtreePoints()
        pointCount = len(allSubtreePoints)
        for p in allSubtreePoints:
            p.hilighted = False

        # Progress bar! Note: array here as it's edited inside the callback.
        pointAt = [0]
        self.canvas.stackWindow.statusBar().showMessage(
            "Registering...  %d/%d points processed." % (pointAt[0], pointCount))
        self.canvas.stackWindow.repaint()
        def progressUpdate(pointsProcessed):
            pointAt[0] += pointsProcessed
            self.canvas.stackWindow.statusBar().showMessage(
                "Registering...  %d/%d points processed." % (pointAt[0], pointCount))

        recursiveAdjust(self.uiState.parent(), windowIndex, branch, pointNew, pointOld, progressUpdate)
        self.uiState.showHilighted = True
        self.canvas.redraw()
        msg = QMessageBox(QMessageBox.Information, "Registration",
            "Registration complete! Unregistered points shown in green, press 'h' to toggle hilight.", parent=self.canvas)
        msg.show()
        self.canvas.stackWindow.statusBar().clearMessage()

    def simpleRegisterImages(self, windowIndex, somaScale=1.01):
        if windowIndex == 0:
            print ("Can't register the first image, nothing to register it against...")
            return
        self.fullActions.history.pushState()

        fullState = self.uiState.parent()
        oldTree = fullState.trees[windowIndex - 1]
        newTree = fullState.trees[windowIndex]
        oldPoints = oldTree.flattenPoints(includeDisconnected=True)
        newPoints = newTree.flattenPoints(includeDisconnected=True)

        # Step 1: Fully change all the IDs of the second scan
        fullNewRemap = {}
        for p in newPoints:
            newID = fullState.nextPointID()
            fullNewRemap[p.id] = newID
            p.id = newID

        # Step 2: Normalize by shifting new tree to match soma location
        oldSomaXYZ = oldTree.rootPoint.location
        newSomaXYZ = newTree.rootPoint.location
        somaShiftDist = util.deltaSz(oldSomaXYZ, newSomaXYZ)
        shift = util.locationMinus(oldSomaXYZ, newSomaXYZ)
        shiftCutoff = max(somaShiftDist * somaScale, 0.001)

        # Step 3: Sort all close pairs (old point, new point) by distance
        shortDistPairs, closestDists = [], []
        for newPoint in newPoints:
            newLoc = newPoint.location
            shiftedNewLoc = util.locationPlus(newLoc, shift)

            closestDist = None
            for oldPoint in oldPoints:
                oldLoc = oldPoint.location
                dist = util.deltaSz(oldLoc, shiftedNewLoc)
                if dist < shiftCutoff:
                    shortDistPairs.append((dist, oldPoint, newPoint))
                if closestDist is None or dist < closestDist:
                    closestDist = dist
                closestDists.append(closestDist)
        shortDistPairs = sorted(shortDistPairs, key=lambda x: x[0])

        # Step 4: Walk through, mapping closest first
        oldToNewMap, newToOldMap, madeUnique = {}, {}, {}
        for (dist, oldPoint, newPoint) in shortDistPairs:
            if dist > shiftCutoff:
                break # shouldn't happen, but just in case

            oldID, newID = oldPoint.id, newPoint.id
            newAlreadyMapped = (newID in newToOldMap) and (not newID in madeUnique)
            oldAlreadyMapped = (oldID in oldToNewMap)
            if (not newAlreadyMapped) and (not oldAlreadyMapped):
                newToOldMap[newID] = oldID
                oldToNewMap[oldID] = newID
                # new point is unmapped and close to old unmapped point, copy ID
                newPoint.id = oldID


    def startReplaceParent(self):
        self.uiState.isReparenting = True
        self.canvas.redraw()

    def stopReplaceParent(self):
        self.uiState.isReparenting = False
        self.canvas.redraw()

    # Cycle selection -> Moving -> Reparenting -> back
    def cyclePointModes(self):
        currentPoint = self.uiState.currentPoint()
        if currentPoint is not None:
            if self.uiState.isMoving:
                # Moving -> Reparenting
                self.fullActions.cancelMove()
                self.startReplaceParent()
            elif self.uiState.isReparenting:
                # Reparenting -> Selection
                self.stopReplaceParent()
            else:
                # Selection -> Moving
                self.fullActions.beginMove(self.windowIndex, currentPoint)