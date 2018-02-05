class FullStateActions():
    def __init__(self, fullState):
        self.state = fullState

    # TODO - move these to dendrite canvas actions
    def addPointToCurrentBranchAndSelect(self, localState, location):
        idx = self.state.indexForState(localState)
        currentBranch = localState.currentBranchIndex
        if idx != -1:
            for i in reversed(range(idx, len(self.state.uiStates))):
                state = self.state.uiStates[i]
                addPointDownstream = True # always true in matlab...
                if addPointDownstream:
                    currentPoint = self.analogousNewPoint(location, currentBranch, idx, i)
                    state.currentBranchIndex = currentBranch
                    state.addPointToCurrentBranchAndSelect(location)

    def addPointToNewBranchAndSelect(self, localState, location):
        idx = self.state.indexForState(localState)
        currentBranch = localState.currentBranchIndex
        currentSource = localState.currentPoint()
        if idx != -1:
            for i in reversed(range(len(self.state.uiStates))):
                state = self.state.uiStates[i]
                addPointDownstream = True # always true in matlab...
                if addPointDownstream:
                    newSource = self.analogousOldPoint(currentSource, currentBranch, idx, i)
                    newPoint = self.analogousNewPoint(location, currentBranch, idx, i)
                    state.selectPoint(newSource)
                    state.addPointToNewBranchAndSelect(newPoint)

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
