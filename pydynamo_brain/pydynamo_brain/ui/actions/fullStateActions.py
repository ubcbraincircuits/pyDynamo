import attr

from PyQt5 import QtWidgets

from .punctaActions import PunctaActions
from .radiiActions import RadiiActions
from .unet.tectalTracing import TectalTracing
from .unet.tectalTracingSoma import TectalTracingFromSoma
from .unet.biocytinTracingSoma import BiocytinTracingFromSoma

from pydynamo_brain.analysis import absOrient
from pydynamo_brain.model import PointMode
from pydynamo_brain.model.tree import *
from pydynamo_brain.ui.branchToColorMap import BranchToColorMap
from pydynamo_brain.ui.common import createAndShowInfo
from pydynamo_brain.util import ImageCache

_IMG_CACHE = ImageCache()

class FullStateActions():
    def __init__(self, fullState, history):
        self.state = fullState
        self.history = history
        self.punctaActions = PunctaActions(fullState, history)
        self.radiiActions = RadiiActions(self, fullState, history)
        self.tectalTracing = TectalTracing(self, fullState, history)
        self.tectalTracingSoma = TectalTracingFromSoma(self, fullState, history)
        self.biocytinTracingSoma = BiocytinTracingFromSoma(self, fullState, history)

        self.branchToColorMap = BranchToColorMap()

    def selectPoint(self, localIdx, point, avoidPush=False, deselectHidden=False):
        if not avoidPush:
            self.history.pushState()
        for state in self.state.uiStates:
            if state.isHidden and deselectHidden:
                state.selectPointByID(None)
            else:
                state.selectPointByID(None if point is None else point.id)

    def selectNextPoints(self, delta=1):
        for state in self.state.uiStates:
            state.selectNextPoint(delta)

    def selectFirstChildren(self):
        for state in self.state.uiStates:
            state.selectFirstChild()

    def findPointOrBranch(self, pointOrBranchID):
        selectedPoint = None
        for tree in self.state.trees:
            # Check point ID first.
            selectedPoint = tree.getPointByID(pointOrBranchID)
            if selectedPoint is None:
                # Not a point, check branch.
                selectedBranch = tree.getBranchByID(pointOrBranchID)
                if selectedBranch is not None and len(selectedBranch) > 0:
                    selectedPoint = selectedBranch.points[0]
            if selectedPoint is not None:
                break

        # Found something to select, so pick it and finish
        if selectedPoint is not None:
            self.selectPoint(0, selectedPoint, avoidPush=True)
            return

    def addPointToCurrentBranchAndSelect(self, localIdx, location):
        self.history.pushState()
        localState = self.state.uiStates[localIdx]
        currentSource = localState.currentPoint()
        newPoint = localState.addPointToCurrentBranchAndSelect(location)
        if newPoint is None:
            # Points exist, but none selected. Skipping.
            return

        newPointBranchID = None if newPoint.isRoot() else newPoint.parentBranch.id
        # If child of the root, make sure to add a color for this branch:
        pointBefore = newPoint.nextPointInBranch(delta=-1)
        if pointBefore is not None and pointBefore.isRoot():
            self.branchToColorMap.updateBranch(newPoint.parentBranch)

        for i in range(localIdx + 1, len(self.state.uiStates)):
            state = self.state.uiStates[i]
            newLocation = self.state.convertLocation(localIdx, i, location, currentSource)
            state.addPointToCurrentBranchAndSelect(newLocation, newPoint.id, newPointBranchID)

    def addPointToNewBranchAndSelect(self, localIdx, location):
        self.history.pushState()
        localState = self.state.uiStates[localIdx]
        currentSource = localState.currentPoint()
        newPoint, newBranch = localState.addPointToNewBranchAndSelect(location)
        self.branchToColorMap.updateBranch(newBranch)

        for i in range(localIdx + 1, len(self.state.uiStates)):
            state = self.state.uiStates[i]
            newLocation = self.state.convertLocation(localIdx, i, location, currentSource)
            state.selectPointByID(currentSource.id)
            state.addPointToNewBranchAndSelect(newLocation, newPoint.id, newBranch.id)

    def addPointMidBranchAndSelect(self, localIdx, location, backwards=False):
        self.history.pushState()

        localState = self.state.uiStates[localIdx]
        currentSource = localState.currentPoint()
        currentBranch = localState.currentBranch()

        newPoint, isAfter = localState.addPointMidBranchAndSelect(location)
        initialState = 0 if backwards else localIdx + 1

        stacks = list(range(localIdx + 1, len(self.state.uiStates)))
        if backwards:
            stacks.extend(list(range(localIdx - 1, -1, -1)))

        for i in stacks:
            state = self.state.uiStates[i]
            newLocation = self.state.convertLocation(localIdx, i, location, currentSource)
            newSource = self.state.analogousPoint(currentSource, localIdx, i)
            newBranch = None if newSource is None else newSource.parentBranch
            # Only add to later ones if the points exist in the tree:
            if newBranch is not None and newSource is not None:
                state.addKnownPointMidBranchAndSelect(
                    newLocation, newBranch, newSource, isAfter, newPoint.id
                )

    def deletePoint(self, localIdx, point, laterStacks):
        self.history.pushState()
        nextToSelect = None
        for i in range(localIdx, len(self.state.uiStates) if laterStacks else localIdx + 1):
            next = self.state.uiStates[i].deletePointByID(point.id)
            if nextToSelect is None:
                nextToSelect = next
        self.selectPoint(localIdx, nextToSelect, avoidPush=True)

    def changeAllZAxis(self, zDelta, originWindow=None):
        self.state.changeAllZAxis(zDelta)

    def nextChannel(self):
        self.history.pushState()
        self.state.changeChannel(1)

    def beginMove(self, localIdx, point):
        self.history.pushState()
        for i in range(len(self.state.uiStates)):
            self.state.uiStates[i].selectPointByID(point.id, isMove=(i >= localIdx))

    def doMove(self, localIdx, dX, dY, downstream, laterStacks):
        for i in range(localIdx, len(self.state.uiStates) if laterStacks else localIdx + 1):
            state = self.state.uiStates[i]
            point = state.currentPoint()
            if point is not None:
                if i == localIdx:
                    point.manuallyMarked = False
                newLocation = (
                    point.location[0] + dX,
                    point.location[1] + dY,
                    point.location[2]
                )
                state.endMove(newLocation, downstream)

    def endMove(self, localIdx, location, downstream, laterStacks):
        self.history.pushState()
        localState = self.state.uiStates[localIdx]
        # Need to copy the point before it gets moved a few lines from now.
        refPoint = localState.currentPoint()
        unmovedPoint = attr.evolve(refPoint)

        for i in range(localIdx, len(self.state.uiStates) if laterStacks else localIdx + 1):
            state = self.state.uiStates[i]
            newLocation = self.state.convertLocation(localIdx, i, location, unmovedPoint)
            state.endMove(newLocation, downstream)

    def cancelMove(self):
        for uiState in self.state.uiStates:
            uiState.cancelMove()

    def reparent(self, localIdx, sourceParent):
        self.history.pushState()
        sourcePoint = self.state.uiStates[localIdx].currentPoint()
        newBranchID = None

        for i, state in enumerate(self.state.uiStates):
            # Find the next down the branch to use as the reparented child...
            childPoint = None
            localSourcePoint = sourcePoint
            while childPoint is None and localSourcePoint is not None:
                childPoint = state._tree.getPointByID(localSourcePoint.id)
                localSourcePoint = localSourcePoint.nextPointInBranch()
            # ... and the previous parent up the branch to use as the new parent.
            newParent = None
            localSourceParent = sourceParent
            while newParent is None and localSourceParent is not None:
                newParent = state._tree.getPointByID(localSourceParent.id)
                localSourceParent = localSourceParent.nextPointInBranch(delta=-1)

            if childPoint is None or newParent is None:
                continue # Ignore, need both points.

            if childPoint.subtreeContainsID(newParent.id):
                print ("Can't set that as the parent, it will cause a loop!")
                return

            oldBranch = childPoint.parentBranch
            newBranchID = state._tree.reparentPoint(childPoint, newParent, newBranchID)
            self.branchToColorMap.updateBranch(oldBranch)
            if newBranchID is not None:
                newBranch = state._tree.getBranchByID(newBranchID)
                self.branchToColorMap.updateBranch(newBranch)

        self.state.uiStates[localIdx].pointMode = PointMode.DEFAULT

    def setSelectedAsPrimaryBranch(self, localIdx):
        """
        For the selected point, and corresponding points in other stacks,
            make it continue its parent's main branch if it's the first in a branch.
        """
        self.history.pushState()
        sourcePoint = self.state.uiStates[localIdx].currentPoint()
        if sourcePoint is None:
            return
        for i, state in enumerate(self.state.uiStates):
            statePoint = state._tree.getPointByID(sourcePoint.id)
            if statePoint is not None:
                state._tree.continueParentBranchIfFirst(statePoint)

    def updateAllPrimaryBranches(self):
        """For each branch point, make the 'primary' branch the longest at that point."""
        self.history.pushState()
        for i, tree in enumerate(self.state.trees):
            tree.updateAllPrimaryBranches()
        self.branchToColorMap.initFromFullState(self.state)

    def updateAllBranchesMinimalAngle(self):
        """For each branch point, make the 'primary' branch with minimal branch deviation."""
        self.history.pushState()
        for i, tree in enumerate(self.state.trees):
            tree.updateAllBranchesMinimalAngle()
        self.branchToColorMap.initFromFullState(self.state)

    def cleanBranchIDs(self):
        """For each branch, set the branch ID to the ID of the first point along it."""
        self.history.pushState()
        for i, tree in enumerate(self.state.trees):
            tree.cleanBranchIDs()
        self.branchToColorMap.initFromFullState(self.state)

    def cleanEmptyBranches(self):
        """For each branch, if it has no points, remove it completely."""
        self.history.pushState()
        totalRemoved = 0
        for i, tree in enumerate(self.state.trees):
            totalRemoved += tree.cleanEmptyBranches()
        return totalRemoved

    def togglePunctaMode(self):
        return self.state.togglePunctaMode()

    def toggleRadiiMode(self):
        return self.state.toggleRadiiMode()

    def toggleManualRegistration(self):
        return self.state.toggleManualRegistrationMode()

    def alignVisibleIDs(self, toNewID=False):
        idToAlign = self.state.nextPointID() if toNewID else None

        for i, state in enumerate(self.state.uiStates):
            if state.isHidden:
                continue # Only register what we can see.
            currentPoint = state.currentPoint()
            if currentPoint is not None:
                if idToAlign is None:
                    idToAlign = currentPoint.id
                elif idToAlign != currentPoint.id:
                    self.state.setPointIDWithoutCollision(self.state.trees[i], currentPoint, idToAlign)

    def getAnnotation(self, localIdx, window, copyToAllPoints):
        self.history.pushState()
        localState = self.state.uiStates[localIdx]
        currentPoint = localState.currentPoint()
        if currentPoint is None:
            return

        title = "Annotate point" + (" in all later stacks" if copyToAllPoints else "")
        text, okPressed = QtWidgets.QInputDialog.getText(window,
            title, "Enter annotation:", QtWidgets.QLineEdit.Normal, currentPoint.annotation)
        if okPressed:
            if copyToAllPoints:
                localID = currentPoint.id
                for i in range(localIdx, len(self.state.trees)):
                    selectedPoint = self.state.trees[i].getPointByID(localID)
                    if selectedPoint is not None:
                        old = selectedPoint.annotation
                        if old is None or old == "" or text.startswith(old) or old.startswith(text):
                            selectedPoint.annotation = text
                        else:
                            selectedPoint.annotation += " " + text
            else:
                currentPoint.annotation = text
