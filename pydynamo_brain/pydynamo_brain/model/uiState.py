from __future__ import annotations

import attr
import math
import numpy as np

from typing import Optional, Tuple, TYPE_CHECKING

from .tree.branch import Branch
from .tree.point import Point
from .tree.tree import Tree

from .pointMode import PointMode

from pydynamo_brain.util import snapToRange, normDelta, dotDelta, deltaSz, SAVE_META, Point3D

if TYPE_CHECKING:
    from .fullState import FullState

@attr.s
class UIState():
    # Full state this belongs within
    _parent: Optional[FullState] = attr.ib(default=None)

    # Tree being shown in the UI.
    _tree: Optional[Tree] = attr.ib(default=None)

    # Path of image, use ImageCache to obtain actual volume
    imagePath: Optional[str] = attr.ib(default=None)

    # Whether the stack is shown or hidden
    isHidden: bool = attr.ib(default=False, metadata=SAVE_META)

    # Which z Axis to display
    zAxisAt: int = attr.ib(default=0, metadata=SAVE_META)

    # ID of currently active point
    currentPointID: Optional[str] = attr.ib(default=None)

    # Cache of the current point
    _currentPointCache: Optional[Point] = attr.ib(default=None)

    # ID of currently active puncta
    currentPunctaID: Optional[str] = attr.ib(default=None)

    # Cache of the current puncta
    _currentPunctaCache: Optional[Point] = attr.ib(default=None)

    # What state the selected point in this stack is in:
    pointMode: PointMode = attr.ib(default=PointMode.DEFAULT)

    # UI Option for whether or not to show annotations.
    showAnnotations: bool = attr.ib(default=False, metadata=SAVE_META)

    # UI Option for whether or not to show IDs (drawn like annotations).
    showIDs: bool = attr.ib(default=False, metadata=SAVE_META)

    # UI Option for which branches to show.
    # 0 = nearby, 1 = all, 2 = only on this Z plane
    branchDisplayMode: int = attr.ib(default=0)

    # UI Option for whether to flatten all z planes into one image.
    zProject: bool = attr.ib(default=False)

    # UI Option for whether or not to show marked points in a different color
    showMarked: bool = attr.ib(default=True)

    # UI Option for whether or not to show *all* the points and dendrites
    hideAll: bool = attr.ib(default=False)

    # (lower-, upper-) bounds for intensities to show
    colorLimits: Tuple[float, float] = attr.ib(default=(0.0, 1.0), metadata=SAVE_META)

    # Name of matplotlib color map to use
    colorMap: Optional[str] = attr.ib(default=None)

    def parent(self) -> Optional[FullState]:
        return self._parent

    def currentBranch(self) -> Optional[Branch]:
        # No branches, or no current point:
        if self._tree is None:
            return None
        if len(self._tree.branches) == 0 or self._currentPointCache is None:
            return None
        if self._currentPointCache.parentBranch is not None:
            return self._currentPointCache.parentBranch
        else:
            # Root point, to place on first branch.
            return self._tree.branches[0]

    def currentPoint(self) -> Optional[Point]:
        return self._currentPointCache

    def currentPuncta(self) -> Optional[Point]:
        return self._currentPunctaCache

    # Point mode checks
    def isMoving(self) -> bool:
        return self.pointMode is PointMode.MOVE

    def isReparenting(self) -> bool:
        return self.pointMode is PointMode.REPARENT

    def deleteBranch(self, branch: Branch) -> None:
        if self._tree is None:
            print ("Can't delete without tree")
            return

        # Need to remove backwards, as we're removing while we're iterating
        reverseIndex = list(reversed(range(len(branch.points))))
        for i in reverseIndex:
            self.deletePointByID(branch.points[i].id)
        self._tree.removeBranch(branch)
        self._currentPointCache = None

    def changeBrightness(self, lowerDelta: float, upperDelta: float) -> None:
        self.colorLimits = (
            snapToRange(self.colorLimits[0] + lowerDelta, 0, self.colorLimits[1] - 0.001),
            snapToRange(self.colorLimits[1] + upperDelta, self.colorLimits[0] + 0.001, 1),
        )

    ## Local actions to apply only to this stack.

    def selectPointByID(self, selectedID: Optional[str], isMove: bool=False) -> None:
        if self._tree is None:
            print ("Can't select without tree")
            return

        self._currentPointCache = None
        if selectedID is not None:
            self._currentPointCache = self._tree.getPointByID(selectedID)

        if self._currentPointCache is not None:
            self.currentPointID = self._currentPointCache.id
            self.pointMode = PointMode.MOVE if isMove else PointMode.DEFAULT
        else:
            if not isMove:
                self.currentPointID = None
                self.pointMode = PointMode.DEFAULT

        # Move z to show point:
        selected = self.currentPoint()
        if selected is not None:
            self.zAxisAt = int(round(selected.location[2]))

    def selectPunctaByID(self, selectedID: str) -> None:
        if self._parent is None:
            print ("Can't select puncta with no fullState")
            return

        self._currentPunctaCache = None
        if selectedID is not None:
            stackIdx = self._parent.uiStates.index(self)
            stackPuncta = None
            if stackIdx < len(self._parent.puncta):
                stackPuncta = self._parent.puncta[stackIdx]
            if stackPuncta is not None:
                for point in stackPuncta:
                    if point.id == selectedID:
                        self._currentPunctaCache = point
                        break

        if self._currentPunctaCache is not None:
            self.currentPunctaID = self._currentPunctaCache.id
            self.zAxisAt = int(round(self._currentPunctaCache.location[2]))
        else:
            self.currentPunctaID = None

    def selectOrDeselectPointID(self, selectedID: str) -> None:
        assert selectedID is not None
        currentPoint = self.currentPoint()
        currentID = None if currentPoint is None else currentPoint.id
        if selectedID != currentID:
            self.selectPointByID(selectedID)
        else:
            self.selectPointByID(None)

    def selectNextPoint(self, delta: int=1) -> None:
        currentPoint = self.currentPoint()
        if currentPoint is None:
            return
        nextPoint = currentPoint.nextPointInBranch(delta)
        self.selectPointByID(nextPoint.id if nextPoint is not None else None)

    def selectFirstChild(self) -> None:
        currentPoint = self.currentPoint()
        if currentPoint is None:
            return
        if len(currentPoint.children) == 0 or len(currentPoint.children[0].points) == 0:
            return
        nextPoint = currentPoint.children[0].points[0]
        self.selectPointByID(nextPoint.id if nextPoint is not None else None)

    def addPointToCurrentBranchAndSelect(self,
        location: Point3D, newPointID: Optional[str]=None, newBranchID: Optional[str]=None
    ) -> Optional[Point]:
        if self._tree is None:
            print ("Can't add point without tree")
            return None

        newPoint = Point(self.maybeCreateNewID(newPointID), location)
        if self._tree.rootPoint is None:
            self._tree.rootPoint = newPoint
        else:
            branch = self.currentBranch()
            if branch is None:
                if len(self._tree.branches) == 0:
                    # First branch, so create it
                    newBranchID = self.maybeCreateBranchID(newBranchID)
                    branch = Branch(newBranchID, self._tree)
                    branch.setParentPoint(self._tree.rootPoint)
                    self._tree.addBranch(branch)
                else:
                    # We have branches, but none selected, so skip this stack.
                    return None
            branch.addPoint(newPoint)
            self._currentPointCache = newPoint
            self.currentPointID = newPoint.id
        return newPoint

    def addPointToNewBranchAndSelect(self,
        location: Point3D, newPointID: Optional[str]=None, newBranchID: Optional[str]=None
    ) -> Tuple[Optional[Point], Optional[Branch]]:
        currentPoint = self.currentPoint()
        if currentPoint is None:
            return None, None

        if self._tree is None:
            print ("Can't add point without tree")
            return None, None

        # Make new branch from current point.
        newBranchID = self.maybeCreateBranchID(newBranchID)
        newBranch = Branch(newBranchID, self._tree)
        newBranch.setParentPoint(currentPoint)
        # Add new point to it.
        newPoint = Point(self.maybeCreateNewID(newPointID), location)
        newBranch.addPoint(newPoint)
        # And update the tree.
        self._tree.addBranch(newBranch)
        self.currentPointID = newPoint.id
        self._currentPointCache = newPoint
        return newPoint, newBranch

    def addPointMidBranchAndSelect(self, location: Point3D) -> Tuple[Optional[Point], bool]:
        branch = self.currentBranch()
        if branch is None:
            return None, False
        currentPoint = self.currentPoint()
        if currentPoint is None:
            return None, False
        currentPointIndex = branch.indexForPoint(currentPoint)

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
        self._currentPointCache = newPoint
        # Returns added point, and whether it was before or after the source
        return newPoint, isAfter

    def addKnownPointMidBranchAndSelect(self,
        location: Point3D, branch: Branch, source: Point, isAfter: bool, newPointID: str
    ) -> None:
        newPoint = Point(newPointID, location)
        newIndex = branch.indexForPoint(source)
        if newIndex == -1:
            assert source.isRoot()
            newIndex = 0
        elif isAfter:
            newIndex += 1
        branch.insertPointBefore(newPoint, newIndex)
        self.currentPointID = newPoint.id
        self._currentPointCache = newPoint

    def deletePointByID(self, pointID: str) -> Optional[Point]:
        if self._tree is None or self._tree.rootPoint is None:
            print ("Can't delete point without tree and soma")
            return None

        if pointID != self._tree.rootPoint.id:
            if len(self._tree.getPointByID(pointID).children) > 0:
                for child in self._tree.getPointByID(pointID).children:
                    self.deleteBranch(child)
            
        return self._tree.removePointByID(pointID)

    def endMove(self, newLocation: Point3D, downstream: bool) -> None:
        if self._tree is None:
            print ("Can't move point without tree")
            return

        if self.isMoving() and self.currentPointID is not None:
            self._tree.movePoint(self.currentPointID, newLocation, downstream)

    def cancelMove(self) -> None:
        self.pointMode = PointMode.DEFAULT

    def cycleBranchDisplayMode(self) -> None:
        N_BRANCH_DISPLAY_MODES = 3 # Local, All Z, Only this Z
        self.branchDisplayMode = (self.branchDisplayMode + 1) % N_BRANCH_DISPLAY_MODES

    def cycleCMAP(self) -> None:
        cmapList = [None, 'magma', 'viridis', 'cividis']
        nextIdx = cmapList.index(self.colorMap) + 1
        if nextIdx < len(cmapList):
            self.colorMap = cmapList[nextIdx]
        else:
            self.colorMap = cmapList[0]

    def cyclePointInfo(self) -> None:
        # show annotations -> showIDs -> show neither -> ...
        if self.showAnnotations:
            self.showAnnotations = False
            self.showIDs = True
        elif self.showIDs:
            self.showAnnotations = False
            self.showIDs = False
        else:
            self.showAnnotations = True
            self.showIDs = False

    def setAllDownstreamPointsMarked(self, marked: bool=True) -> None:
        selected = self.currentPoint()
        if selected is None and self._tree is not None:
            selected = self._tree.rootPoint
        if selected is None:
            return
        for point in selected.flattenSubtreePoints():
            point.manuallyMarked = marked

    def maybeCreateNewID(self, newPointID: Optional[str]) -> str:
        assert self._parent is not None
        return newPointID if newPointID is not None else self._parent.nextPointID()

    def maybeCreateBranchID(self, newBranchID: Optional[str]) -> str:
        assert self._parent is not None
        return newBranchID if newBranchID is not None else self._parent.nextBranchID()
