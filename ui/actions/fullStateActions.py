import attr

from PyQt5 import QtWidgets

from analysis import absOrient

from model.tree import *

class FullStateActions():
    def __init__(self, fullState, history):
        self.state = fullState
        self.history = history

    def selectPoint(self, localIdx, point, avoidPush=False):
        if not avoidPush:
            self.history.pushState()
        for state in self.state.uiStates:
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

        for i in range(localIdx + 1, len(self.state.uiStates)):
            state = self.state.uiStates[i]
            newLocation = self.state.convertLocation(localIdx, i, location, currentSource)
            state.addPointToCurrentBranchAndSelect(newLocation, newPoint.id, newPointBranchID)

    def addPointToNewBranchAndSelect(self, localIdx, location):
        self.history.pushState()
        localState = self.state.uiStates[localIdx]
        currentSource = localState.currentPoint()
        newPoint, newBranch = localState.addPointToNewBranchAndSelect(location)

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
            newBranch = self.state.analogousBranch(currentBranch, localIdx, i)
            newSource = self.state.analogousPoint(currentSource, localIdx, i)
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

    def changeAllZAxis(self, zDelta):
        self.state.changeAllZAxis(zDelta)

    def nextChannel(self):
        self.history.pushState()
        self.state.changeChannel(1)

    def beginMove(self, localIdx, point):
        self.history.pushState()
        for i in range(len(self.state.uiStates)):
            self.state.uiStates[i].selectPointByID(point.id, isMove=(i >= localIdx))

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

    def setLandmark(self, localIdx, location):
        self.history.pushState()
        self.state.setLandmark(localIdx, location)

    def deleteCurrentLandmark(self):
        self.history.pushState()
        self.state.deleteLandmark(self.state.landmarkPointAt)

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
            newBranchID = state._tree.reparentPoint(childPoint, newParent, newBranchID)

        self.state.uiStates[localIdx].isReparenting = False

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
        for i, state in enumerate(self.state.uiStates):
            state._tree.updateAllPrimaryBranches()

    def calculateBestOrientation(self):
        X0, Y0, Z0 = self.state.trees[0].worldCoordPoints(self.state.landmarks[0])

        for i in range(0, len(self.state.landmarks)):
            Xi, Yi, Zi = self.state.trees[i].worldCoordPoints(self.state.landmarks[i])
            matchIdx = []
            for j in range(len(Xi)):
                if Xi[j] is not None and j < len(X0) and X0[j] is not None:
                    matchIdx.append(j)
            if (len(matchIdx) < 3):
                # TODO - pull out of here, pass in callback for error skips instead
                msg = "Scan [%d] skipped: %d landmarks match initial, need 3." % (i+1, len(matchIdx))
                msg = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Information, msg, msg)
                msg.show()
                continue
            pointsFrom = [(Xi[j], Yi[j], Zi[j]) for j in matchIdx]
            pointsTo = [(X0[j], Y0[j], Z0[j]) for j in matchIdx]
            fit, R, T = absOrient(pointsFrom, pointsTo)
            # tolist() as state should not have (unsavable) numpy data
            self.state.trees[i].transform.rotation = R.tolist()
            self.state.trees[i].transform.translation = T.tolist()

    def toggleManualRegistration(self):
        return self.state.toggleManualRegistrationMode()

    def alignIDs(self):
        idToAlign = None
        remaps = {}
        for i, state in enumerate(self.state.uiStates):
            currentPoint = state.currentPoint()
            if currentPoint is not None:
                if idToAlign is None:
                    idToAlign = currentPoint.id
                elif idToAlign != currentPoint.id:
                    if i not in remaps:
                        remaps[i] = []
                    remaps[i].extend(
                        self.state.setPointIDWithoutCollision(self.state.trees[i], currentPoint, idToAlign)
                    )
        self.state.appendIDRemap(remaps)

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
