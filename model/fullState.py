import attr

from .options import ProjectOptions
from .tree import *
from .uiState import *

from util import SAVE_META

@attr.s
class FullState:
    # Root path this data is saved to:
    _rootPath = attr.ib(default=None)

    # Paths to *.tif image files.
    filePaths = attr.ib(default=attr.Factory(list), metadata=SAVE_META)

    # Image-specific tree data, one for each of the files above
    trees = attr.ib(default=attr.Factory(list), metadata=SAVE_META)

    # Landmark points for each tree.
    landmarks = attr.ib(default=attr.Factory(list), metadata=SAVE_META)

    # Image-specific options, one for each of the files above
    uiStates = attr.ib(default=attr.Factory(list), metadata=SAVE_META)

    # Project options
    projectOptions = attr.ib(default=attr.Factory(ProjectOptions), metadata=SAVE_META)

    # Size of volume (# channels, x, y, z), needs to be the same between stacks
    volumeSize = attr.ib(default=None)

    # Shared UI position in the Z plane
    zAxisAt = attr.ib(default=0)

    # Shared color channel information
    channel = attr.ib(default=0)

    # Which landmark point we're editing, -1 when not in landmark mode.
    landmarkPointAt = attr.ib(default=-1)

    # Whether to draw channels in color (True for r/g/b) or white (False)
    useColor = attr.ib(default=False)

    # Shared UI Option for dendrite line width
    lineWidth = attr.ib(default=3)

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

    def changeZAxis(self, delta):
        self.zAxisAt = snapToRange(self.zAxisAt + delta, 0, self.volumeSize[1] - 1)

    def changeChannel(self, delta):
        self.channel = (self.channel + delta) % self.volumeSize[0]

    def inLandmarkMode(self):
        return self.landmarkPointAt >= 0

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

    def convertLocation(self, sourceLocation, sourceID, targetID):
        # given a point, pass it through the transformation from source to
        # target, with the branch base as the translation reference source
        # and landmarks as the rotation reference. return the position.
        noRotation = True # all(all(state{targetID}.info.R == eye(3))) || isempty(state{targetID}.info.R)
        if sourceID == targetID or noRotation:
            return sourceLocation
        # TODO - rotation logic, see matlab.
        return sourceLocation # HACK - support rotations

    def analogousPoint(self, sourcePoint, sourceID, targetID):
        if sourceID == targetID:
            return sourcePoint
        return self.uiStates[targetID]._tree.getPointByID(sourcePoint.id)

    def analogousBranch(self, sourceBranch, sourceID, targetID):
        if sourceBranch == None or sourceID == targetID:
            return sourceBranch
        return self.uiStates[targetID]._tree.getBranchByID(sourceBranch.id)

    def nextPointID(self):
        newID = '%08x' % self._nextPointID
        self._nextPointID += 1
        return newID

    def nextBranchID(self):
        newID = '%04x' % self._nextBranchID
        self._nextBranchID += 1
        return newID

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
