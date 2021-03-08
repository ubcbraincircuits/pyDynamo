import attr

from typing import List, Optional, Tuple

from .options import ProjectOptions
from .tree.branch import Branch
from .tree.point import Point
from .tree.tree import Tree

from .drawMode import DrawMode
from .uiState import UIState

from pydynamo_brain.util import SAVE_META, ImageCache, locationMinus, locationPlus, Point3D

_IMG_CACHE = ImageCache()

@attr.s
class FullState:
    # Root path this data is saved to:
    _rootPath: Optional[str] = attr.ib(default=None)

    # Paths to *.tif image files.
    filePaths: List[str] = attr.ib(default=attr.Factory(list), metadata=SAVE_META)

    # Image-specific tree data, one for each of the files above
    trees: List[Tree] = attr.ib(default=attr.Factory(list), metadata=SAVE_META)

    # Puncta points (mapping id -> Point), for each stack.
    puncta: List[List[Point]] = attr.ib(default=attr.Factory(list), metadata=SAVE_META)

    # Paths to *.nwb files of per-POI recorded traces, for each stack.
    traces: List[str] = attr.ib(default=attr.Factory(list), metadata=SAVE_META)

    # Image-specific options, one for each of the files above
    uiStates: List[UIState] = attr.ib(default=attr.Factory(list), metadata=SAVE_META)

    # Project options
    projectOptions: ProjectOptions = attr.ib(default=attr.Factory(ProjectOptions), metadata=SAVE_META)

    # Size of volume (# channels, x, y, z), needs to be the same between stacks
    volumeSize: Optional[List[int]] = attr.ib(default=None)

    # Shared color channel information
    channel: int = attr.ib(default=0)

    # What drawing mode the user is currently in (normal, puncta, radii, registration)
    drawMode: DrawMode = attr.ib(default=DrawMode.DEFAULT)

    # Whether to draw channels in color (True for r/g/b) or white (False)
    useColor: bool = attr.ib(default=False)

    # Shared UI Option for dendrite line width
    lineWidth: int = attr.ib(default=3)

    # Shared UI Option for diameter of point circles
    dotSize: Optional[int] = attr.ib(default=5)

    # Keep track of the ID for the next point created, used for making more unique identifiers.
    _nextPointID: int = 0

    # Keep track of the ID for the next branch created, used for making more unique identifiers.
    _nextBranchID: int = 0

    # Get the index of a state, or -1 if it's not contained.
    def indexForState(self, uiState: UIState) -> int:
        try:
            return self.uiStates.index(uiState)
        except:
            return -1

    # Draw status
    def inDrawMode(self) -> bool:
        return self.drawMode == DrawMode.DEFAULT

    def inPunctaMode(self) -> bool:
        return self.drawMode == DrawMode.PUNCTA

    def inManualRegistrationMode(self) -> bool:
        return self.drawMode == DrawMode.REGISTRATION

    def inRadiiMode(self) -> bool:
        return self.drawMode == DrawMode.RADII

    # TODO: active window
    # TODO: add new window off active

    def addFiles(self, filePaths: List[str], treeData: Optional[List[Tree]]=None) -> None:
        for i, path in enumerate(filePaths):
            self.filePaths.append(path)

            nextTree = Tree() # TODO: add nextTree as child of prevTree
            if treeData is not None and i < len(treeData):
                nextTree = treeData[i]
            self.trees.append(nextTree)

            uiState = UIState(parent=self, tree=nextTree)
            self.uiStates.append(uiState)
            nextTree._parentState = uiState

    def toggleLineWidth(self) -> None:
        if self.lineWidth == 4:
            self.lineWidth = 1
        else:
            self.lineWidth += 1

    def toggleDotSize(self) -> None:
        if self.dotSize is None:
            self.dotSize = 3
        elif self.dotSize == 9:
            self.dotSize = None
        else:
            self.dotSize += 2

    def changeAllZAxis(self, floatDelta: float) -> None:
        delta: int = int(round(floatDelta))
        if delta == 0:
            return

        highestZ = None # Highest Z = max to scroll backwards
        highestLeft = None # Highest left = max to scroll forwards

        for uiState in self.uiStates:
            maybeVolume = _IMG_CACHE.getVolumeIfLoaded(uiState.imagePath)
            if maybeVolume is None:
                # Volume not yet loaded, ignore
                continue

            zDim = maybeVolume.shape[1] # C, Z, X, Y

            if highestZ is None:
                highestZ = uiState.zAxisAt
                highestLeft = zDim - 1 - uiState.zAxisAt
            else:
                highestZ = max(highestZ, uiState.zAxisAt)
                highestLeft = max(highestLeft, zDim - 1 - uiState.zAxisAt)

        # Make sure that we're in at least one volume by the end of the scroll:
        if delta < 0 and highestZ is not None:
            delta = -min(-delta, highestZ)
        elif highestLeft is not None:
            delta = min(delta, highestLeft)

        for uiState in self.uiStates:
            uiState.zAxisAt += delta

    def changeChannel(self, delta: int) -> None:
        if self.volumeSize is not None and len(self.volumeSize) > 0:
            self.channel = (self.channel + delta) % self.volumeSize[0]

    def togglePunctaMode(self) -> None:
        self.drawMode = DrawMode.DEFAULT if self.inPunctaMode() else DrawMode.PUNCTA

    def toggleRadiiMode(self) -> None:
        self.drawMode = DrawMode.DEFAULT if self.inRadiiMode() else DrawMode.RADII

    def toggleManualRegistrationMode(self) -> None:
        self.drawMode = DrawMode.DEFAULT if self.inManualRegistrationMode() else DrawMode.REGISTRATION

    def updateVolumeSize(self, volumeSize: List[int]) -> None:
        # TODO: Something better when volume sizes don't match? ...
        if self.volumeSize is None:
            self.volumeSize = volumeSize

    def convertLocation(self,
        sourceID: int, targetID: int, sourceLocation: Point3D, sourcePointBefore: Optional[Point]=None
    ) -> Point3D:
        # TODO: Use stack transform once registration is useful?
        # TODO: Also perhaps use pointAfter to guide even better when it exists.
        if sourcePointBefore is None:
            return sourceLocation # No reference point, so just copy.

        # Walk backwards until we find a point in both stacks to use as a reference
        targetPointBefore = None
        while sourcePointBefore is not None and targetPointBefore is None:
            targetPointBefore = self.analogousPoint(sourcePointBefore, sourceID, targetID)
            if targetPointBefore is None:
                sourcePointBefore = sourcePointBefore.nextPointInBranch(delta=-1)

        if targetPointBefore is None:
            return sourceLocation # Still no upstream reference point, so copy.

        # Keep same delta. Loc_source - PB_source = Delta = Loc_target - PB_target
        # So Loc_target = PB_target + (Loc_source - PB_source)
        if sourcePointBefore is None:
            return targetPointBefore.location

        sourceDelta = locationMinus(sourceLocation, sourcePointBefore.location)
        return locationPlus(targetPointBefore.location, sourceDelta)

    def analogousPoint(self,
        sourcePoint: Optional[Point], sourceID: int, targetID: int
    ) -> Optional[Point]:
        if sourcePoint is None or sourceID == targetID:
            return sourcePoint
        tree = self.uiStates[targetID]._tree
        if tree is not None:
            return tree.getPointByID(sourcePoint.id)
        return None

    def removeStack(self, index: int) -> None:
        self.filePaths.pop(index)
        self.trees.pop(index)
        self.uiStates.pop(index)
        # TODO - remove undo state for that stack too

    def colorChannel(self) -> Optional[str]:
        if not self.useColor:
            return None
        return ['r', 'g', 'b'][self.channel % 3]

    def setPointIDWithoutCollision(self, tree: Tree, point: Point, newID: str) -> None:
        """Change the ID of a point in a tree, making sure it doesn't collide with an existing point."""
        if point.id == newID:
            return

        existingWithID = tree.getPointByID(newID)
        if existingWithID == point:
            return

        if existingWithID is not None:
            # There's already a point with this ID - change it to a new ID.
            existingWithID.id = self.nextPointID()

        point.id = newID

    def setBranchIDWithoutCollision(self, tree: Tree, branch: Branch, newID: str) -> None:
        """Same as setPointIDWithoutCollision, but with branches instead of points."""
        if branch.id == newID:
            return

        existingWithID = tree.getBranchByID(newID)
        if existingWithID == branch:
            return

        if existingWithID is not None:
            # There's already a branch with this ID - change it to a new ID.
            existingWithID.id = self.nextBranchID()

        branch.id = newID

    def nextPointID(self) -> str:
        newID = '%08x' % self._nextPointID
        self._nextPointID += 1
        return newID

    def nextBranchID(self) -> str:
        newID = '%04x' % self._nextBranchID
        self._nextBranchID += 1
        return newID
