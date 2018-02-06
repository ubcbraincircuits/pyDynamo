from .tree import *

class FullStateActions():
    def __init__(self, fullState):
        self.state = fullState

    def selectPoint(self, localIdx, point):
        localState = self.state.uiStates[localIdx]
        currentBranch = localState.currentBranchIndex
        for i in reversed(range(len(self.state.uiStates))):
            state = self.state.uiStates[i]
            selectedPoint = self.analogousOldPoint(point, currentBranch, localIdx, i)
            state.selectPoint(selectedPoint)

    def addPointToCurrentBranchAndSelect(self, localIdx, location):
        localState = self.state.uiStates[localIdx]
        currentBranch = localState.currentBranchIndex
        for i in reversed(range(localIdx, len(self.state.uiStates))):
            state = self.state.uiStates[i]
            currentPoint = self.analogousNewPoint(location, currentBranch, localIdx, i)
            state.currentBranchIndex = currentBranch
            state.addPointToCurrentBranchAndSelect(location)

    def addPointToNewBranchAndSelect(self, localIdx, location):
        localState = self.state.uiStates[localIdx]
        currentBranch = localState.currentBranchIndex
        currentSource = localState.currentPoint()
        for i in reversed(range(len(self.state.uiStates))):
            state = self.state.uiStates[i]
            addPointDownstream = True # always true in matlab...
            if addPointDownstream:
                newSource = self.analogousOldPoint(currentSource, currentBranch, localIdx, i)
                newPoint = self.analogousNewPoint(location, currentBranch, localIdx, i)
                state.selectPoint(newSource)
                state.addPointToNewBranchAndSelect(newPoint)

    def addPointMidBranchAndSelect(self, localIdx, location):
        localState = self.state.uiStates[localIdx]
        currentBranch = localState.currentBranchIndex
        branch, pointAfter = localState.addPointMidBranchAndSelect(location)
        for i in reversed(range(localIdx + 1, len(self.state.uiStates))):
            state = self.state.uiStates[i]
            newBranch = self.analogousBranch(branch, localIdx, i)
            if pointAfter is None:
                newPointIndex = len(newBranch.points)
            else:
                newAfter = self.analogousOldPoint(pointAfter, currentBranch, localIdx, i)
                newPointIndex = newBranch.points.index(newAfter)
            newBranch.insertPointBefore(Point(location), newPointIndex)

    def deletePoint(self, localIdx, point):
        localState = self.state.uiStates[localIdx]
        # TODO: Delete point vs delete entire branch of point
        currentBranch = localState.currentBranchIndex
        currentSource = localState.currentPoint()
        if localIdx != -1:
            for i in reversed(range(localIdx, len(self.state.uiStates))):
                newSource = self.analogousOldPoint(currentSource, currentBranch, localIdx, i)
                self.state.uiStates[i].deletePoint(newSource)

    ##
    ## ANALOGOUS methods
    ## TODO: fix up ID system, do properly.
    ##

    def analogousNewPoint(self, sourcePosition, sourceBranch, sourceID, targetID):
        # given a point, pass it through the transformation from source to
        # target, with the branch base as the translation reference source
        # and landmarks as the rotation reference. return the position.
        noRotation = True # all(all(state{targetID}.info.R == eye(3))) || isempty(state{targetID}.info.R)
        if sourceID == targetID or noRotation:
            return sourcePosition

        # TODO - rotation logic, see matlab.
        return sourcePosition # HACK - support rotations

    def analogousOldPoint(self, sourcePoint, sourceBranch, sourceID, targetID):
        # TODO - rotation logic, see matlab.
        if sourceID == targetID:
            return sourcePoint
        return self.state.uiStates[targetID]._tree.closestPointTo(sourcePoint.location)

    def analogousBranch(self, branch, sourceID, targetID):
        if sourceID == targetID:
            return branch;
        idx = self.state.uiStates[sourceID]._tree.branches.index(branch)
        return self.state.uiStates[targetID]._tree.branches[idx]
