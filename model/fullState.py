import attr

from .options import ProjectOptions
from .tree.branch import Branch
from .tree.point import Point
from .tree.tree import Tree
from .uiState import *

from util import SAVE_META, ImageCache, locationMinus, locationPlus

_IMG_CACHE = ImageCache()

@attr.s
class FullState:
    # Root path this data is saved to:
    _rootPath = attr.ib(default=None)

    # Paths to *.tif image files.
    filePaths = attr.ib(default=attr.Factory(list), metadata=SAVE_META)

    # Image-specific tree data, one for each of the files above
    trees = attr.ib(default=attr.Factory(list), metadata=SAVE_META)

    # Landmark points for each stack.
    landmarks = attr.ib(default=attr.Factory(list), metadata=SAVE_META)

    # Puncta points (mapping id -> Point) for each stack.
    puncta = attr.ib(default=attr.Factory(list), metadata=SAVE_META)

    # Image-specific options, one for each of the files above
    uiStates = attr.ib(default=attr.Factory(list), metadata=SAVE_META)

    # Project options
    projectOptions = attr.ib(default=attr.Factory(ProjectOptions), metadata=SAVE_META)

    # Size of volume (# channels, x, y, z), needs to be the same between stacks
    volumeSize = attr.ib(default=None)

    # Shared color channel information
    channel = attr.ib(default=0)

    # Whether we're currently drawing puncta
    inPunctaMode = attr.ib(default=False)

    # Which landmark point we're editing, -1 when not in landmark mode.
    landmarkPointAt = attr.ib(default=-1)

    # Whether to draw channels in color (True for r/g/b) or white (False)
    useColor = attr.ib(default=False)

    # Shared UI Option for dendrite line width
    lineWidth = attr.ib(default=3)

    # Shared UI Option for diameter of point circles
    dotSize = attr.ib(default=5)

    # ID remap for manual registration mode, or none if not in manual registration.
    manualRegistrationIDRemap = attr.ib(default=None)

    # Keep track of the ID for the next point created, used for making more unique identifiers.
    _nextPointID = 0

    # Keep track of the ID for the next branch created, used for making more unique identifiers.
    _nextBranchID = 0

    # Get the index of a state, or -1 if it's not contained.
    def indexForState(self, uiState):
        try:
            return self.uiStates.index(uiState)
        except:
            return -1

    # TODO: active window
    # TODO: add new window off active

    def addFiles(self, filePaths, treeData=None, landmarkData=None):
        for i, path in enumerate(filePaths):
            self.filePaths.append(path)

            nextTree = Tree() # TODO: add nextTree as child of prevTree
            if treeData is not None and i < len(treeData):
                nextTree = treeData[i]
            self.trees.append(nextTree)

            nextLandmarks = []
            if landmarkData is not None and i < len(landmarkData):
                nextLandmarks = landmarkData[i]
            self.landmarks.append(nextLandmarks)

            uiState = UIState(parent=self, tree=nextTree)
            self.uiStates.append(uiState)
            nextTree._parentState = uiState

    def toggleLineWidth(self):
        if self.lineWidth == 4:
            self.lineWidth = 1
        else:
            self.lineWidth += 1

    def toggleDotSize(self):
        if self.dotSize is None:
            self.dotSize = 3
        elif self.dotSize == 9:
            self.dotSize = None
        else:
            self.dotSize += 2

    def changeAllZAxis(self, delta):
        delta = int(round(delta))

        scrollForwards, scrollBackwards = None, None
        for uiState in self.uiStates:
            uiState.zAxisAt += delta
            zCount = _IMG_CACHE.getVolume(uiState.imagePath).shape[1] # C, Z, X, Y
            if scrollForwards is None:
                scrollForwards, scrollBackwards = -uiState.zAxisAt, uiState.zAxisAt + 1 - zCount
            else:
                scrollForwards = min(scrollForwards, -uiState.zAxisAt)
                scrollBackwards = min(scrollBackwards, uiState.zAxisAt + 1 - zCount)

        # If scrolling past the ends, snap back:
        if scrollForwards > 0:
            for uiState in self.uiStates:
                uiState.zAxisAt += scrollForwards
        elif scrollBackwards > 0:
            for uiState in self.uiStates:
                uiState.zAxisAt -= scrollBackwards

    def changeChannel(self, delta):
        self.channel = (self.channel + delta) % self.volumeSize[0]

    def inDrawMode(self):
        return not self.inLandmarkMode() \
            and not self.inManualRegistrationMode() \
            and not self.inPunctaMode

    def inLandmarkMode(self):
        return self.landmarkPointAt >= 0

    def inManualRegistrationMode(self):
        return self.manualRegistrationIDRemap is not None

    def togglePunctaMode(self):
        isInMode = self.inPunctaMode
        if isInMode:
            self.inPunctaMode = False
        else:
            if self.inLandmarkMode():
                self.landmarkPointAt = -1
            elif self.inManualRegistrationMode():
                self.toggleManualRegistrationMode()
            self.inPunctaMode = True

    def toggleManualRegistrationMode(self):
        isInMode = self.inManualRegistrationMode()
        if isInMode:
            idRemap = self.manualRegistrationIDRemap
            self.manualRegistrationIDRemap = None
            return idRemap
        else:
            if self.inLandmarkMode():
                self.landmarkPointAt = -1
            self.manualRegistrationIDRemap = []
            return None

    def appendIDRemap(self, idRemaps):
        for stepID, idRemapList in idRemaps.items():
            while len(self.manualRegistrationIDRemap) <= stepID:
                self.manualRegistrationIDRemap.append([])
            self.manualRegistrationIDRemap[stepID].extend(idRemapList)

    def toggleLandmarkMode(self):
        self.landmarkPointAt = -1 if self.inLandmarkMode() else 0

    def nextLandmarkPoint(self, backwards=False):
        self.landmarkPointAt += -1 if backwards else 1
        self.landmarkPointAt = max(0, self.landmarkPointAt)

    def deleteLandmark(self, landmarkId):
        for landmarks in self.landmarks:
            if landmarkId < len(landmarks):
                landmarks.pop(landmarkId)

    def updateVolumeSize(self, volumeSize):
        # TODO: Something better when volume sizes don't match? ...
        if self.volumeSize is None:
            self.volumeSize = volumeSize

    def convertLocation(self, sourceID, targetID, sourceLocation, sourcePointBefore=None):
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
        sourceDelta = locationMinus(sourceLocation, sourcePointBefore.location)
        return locationPlus(targetPointBefore.location, sourceDelta)

    def analogousPoint(self, sourcePoint, sourceID, targetID):
        if sourcePoint is None or sourceID == targetID:
            return sourcePoint
        return self.uiStates[targetID]._tree.getPointByID(sourcePoint.id)

    def analogousBranch(self, sourceBranch, sourceID, targetID):
        if sourceBranch == None or sourceID == targetID:
            return sourceBranch
        return self.uiStates[targetID]._tree.getBranchByID(sourceBranch.id)

    def removeStack(self, index):
        self.filePaths.pop(index)
        self.trees.pop(index)
        self.landmarks.pop(index)
        self.uiStates.pop(index)
        # TODO - remove undo state for that stack too

    def colorChannel(self):
        if not self.useColor:
            return None
        return ['r', 'g', 'b'][self.channel % 3]

    def setLandmark(self, treeIndex, location):
        assert self.landmarkPointAt >= 0
        while len(self.landmarks[treeIndex]) <= self.landmarkPointAt:
            self.landmarks[treeIndex].append(None)
        self.landmarks[treeIndex][self.landmarkPointAt] = location

    def setPointIDWithoutCollision(self, tree, point, newID):
        """Change the ID of a point in a tree, making sure it doesn't collide with an existing point."""
        if point.id == newID:
            return
        existingWithID = tree.getPointByID(newID)
        if existingWithID == point:
            return
        remaps = []
        if existingWithID is not None:
            # There's already a point with this ID - change it to a new ID.
            fixedID = self.nextPointID()
            remaps.append((existingWithID.id, fixedID))
            existingWithID.id = fixedID
        remaps.append((point.id, newID))
        point.id = newID
        # Return a list of ID remaps: (oldID, newID). Will either be one, or two if collision.
        return remaps

    def setBranchIDWithoutCollision(self, tree, branch, newID):
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
        # No return for this one, can be added if needed.

    def nextPointID(self):
        newID = '%08x' % self._nextPointID
        self._nextPointID += 1
        return newID

    def nextBranchID(self):
        newID = '%04x' % self._nextBranchID
        self._nextBranchID += 1
        return newID
