import attr
import math

from .tree import *

from util import snapToRange, normDelta, dotDelta, deltaSz, SAVE_META

@attr.s
class UIState():
    # Full state this belongs within
    _parent = attr.ib(default=None)

    # Tree being shown in the UI.
    _tree = attr.ib(default=None)

    # 3D tensor of intensities for image voxels
    imageVolume = attr.ib(default=None)

    # ID of currently active branch
    currentBranchID = attr.ib(default=None)

    # ID of currently active point
    currentPointID = attr.ib(default=None)

    # Whether the current point is being moved (True) or just selected (False)
    isMoving = attr.ib(default=False)

    # UI Option for whether or not to show annotations.
    showAnnotations = attr.ib(default=True, metadata=SAVE_META)

    # UI Option for whether or not to show all branches, or just the nearby ones.
    drawAllBranches = attr.ib(default=False, metadata=SAVE_META)

    # (lower-, upper-) bounds for intensities to show
    colorLimits = attr.ib(default=(0, 1), metadata=SAVE_META)

    def parent(self):
        return self._parent

    def currentBranch(self):
        return self._tree.getBranchByID(self.currentBranchID)

    def setImageVolume(self, newData):
        self.imageVolume = np.array(newData)
        self._parent.updateVolumeSize(self.imageVolume.shape)

    def currentImage(self):
        return self.imageVolume[self._parent.channel][self._parent.zAxisAt]

    def currentPoint(self):
        if self.currentPointID is None:
            return self._tree.rootPoint
        return self._tree.getPointByID(self.currentPointID)

    def deleteBranch(self, branch):
        # Need to remove backwards, as we're removing while we're iterating
        reverseIndex = list(reversed(range(len(branch.points))))
        for i in reverseIndex:
            self.deletePointByID(branch.points[i].id)
        self._tree.removeBranch(branch)

    def changeBrightness(self, lowerDelta, upperDelta):
        self.colorLimits = (
            snapToRange(self.colorLimits[0] + lowerDelta, 0, self.colorLimits[1] - 0.001),
            snapToRange(self.colorLimits[1] + upperDelta, self.colorLimits[0] + 0.001, 1),
        )

    ## Local actions to apply only to this stack.

    def selectPointByID(self, selectedID, isMove=False):
        selectedPoint = self._tree.getPointByID(selectedID)
        if selectedPoint is not None:
            self.currentPointID = selectedID
            if selectedPoint.isRoot():
                if len(self._tree.branches) > 0:
                    self.currentBranchID = self._tree.branches[0].id
                else:
                    self.currentBranchID = None
            else:
                self.currentBranchID = selectedPoint.parentBranch.id
            self.isMoving = isMove
        else:
            self.currentPointID = None
            self.currentBranchID = None
            self.isMoving = False
            assert not isMove

    def addPointToCurrentBranchAndSelect(self, location, newPointID=None, newBranchID=None):
        newPoint = Point(self.maybeCreateNewID(newPointID), location)
        if self._tree.rootPoint is None:
            self._tree.rootPoint = newPoint
        else:
            if self.currentBranchID is None:
                newBranchID = self.maybeCreateBranchID(newBranchID)
                newBranch = Branch(newBranchID, self._tree)
                newBranch.setParentPoint(self._tree.rootPoint)
                self._tree.addBranch(newBranch)
                self.currentBranchID = newBranch.id
            self.currentBranch().addPoint(newPoint)
            self.currentPointID = newPoint.id
        return newPoint

    def addPointToNewBranchAndSelect(self, location, newPointID=None, newBranchID=None):
        newPoint = Point(self.maybeCreateNewID(newPointID), location)
        newBranchID = self.maybeCreateBranchID(newBranchID)
        newBranch = Branch(newBranchID, self._tree)
        newBranch.setParentPoint(self.currentPoint())
        newBranch.addPoint(newPoint)
        self._tree.addBranch(newBranch)
        self.currentBranchID = newBranch.id
        self.currentPointID = newPoint.id
        return newPoint, newBranch

    def addPointMidBranchAndSelect(self, location):
        branch = self.currentBranch()
        if branch is None:
            return None, False

        currentPoint = self.currentPoint()
        currentPointIndex = branch.indexForPoint(self.currentPoint())
        newPoint = Point(self.maybeCreateNewID(None), location)
        newPointIndex = None
        isAfter = False

        if currentPointIndex == -1:
            # Selected the root point in the first branch, so add before the first point
            newPointIndex = 0
            isAfter = True
        elif len(branch.points) < 2:
            # Branch is either empty or has only one point, so add new point at start:
            newPointIndex = 0
            isAfter = (len(branch.points) == 0)
        elif currentPointIndex == len(branch.points) - 1:
            # Current = last point in branch, so add new point before it:
            newPointIndex = currentPointIndex
            isAfter = False
        else:
            beforePoint = branch.parentPoint if currentPointIndex == 0 else branch.points[currentPointIndex - 1]
            afterPoint = branch.points[currentPointIndex + 1]
            if beforePoint is None:
                return None, False # Something's gone wrong, ignore

            beforeDelta = normDelta(beforePoint.location, currentPoint.location)
            afterDelta = normDelta(afterPoint.location, currentPoint.location)
            currDelta = normDelta(location, currentPoint.location)
            isAfter = (dotDelta(beforeDelta, currDelta) < dotDelta(afterDelta, currDelta))
            newPointIndex = currentPointIndex + (1 if isAfter else 0)

        branch.insertPointBefore(newPoint, newPointIndex)
        self.currentPointID = newPoint.id
        # Returns added point, and whether it was before or after the source
        return newPoint, isAfter

    def addKnownPointMidBranchAndSelect(self, location, branch, source, isAfter, newPointID):
        newPoint = Point(newPointID, location)
        newIndex = branch.indexForPoint(source)
        if newIndex == -1:
            assert source.isRoot()
            newIndex = 0
        elif isAfter:
            newIndex += 1
        branch.insertPointBefore(newPoint, newIndex)
        self.currentBranchID = branch.id
        self.currentPointID = newPoint.id

    def deletePointByID(self, pointID):
        for branch in self._tree.branches:
            if branch.parentPoint.id == pointID:
                self.deleteBranch(branch)
        return self._tree.removePointByID(pointID)

    def endMove(self, newLocation, moveDownstream):
        assert self.isMoving and self.currentPointID is not None, "Can only end a move if actually moving a point"
        self._tree.movePoint(self.currentPointID, newLocation, moveDownstream)


    def maybeCreateNewID(self, newPointID):
        return newPointID if newPointID is not None else self._parent.nextPointID()

    def maybeCreateBranchID(self, newBranchID):
        return newBranchID if newBranchID is not None else self._parent.nextBranchID()
