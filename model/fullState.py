import attr

from .tree import *
from .uiState import *

@attr.s
class FullState:
    # Paths to *.tif image files.
    filePaths = attr.ib(default=attr.Factory(list))

    # Image-specific tree data, one for each of the files above
    trees = attr.ib(default=attr.Factory(list))

    # Image-specific options, one for each of the files above
    uiStates = attr.ib(default=attr.Factory(list))

    # Size of 3D volume, needs to be the same between stacks
    volumeSize = attr.ib(default=None)

    # Shared UI position in the Z plane
    zAxisAt = attr.ib(default=0)

    # Shared UI Option for dendrite line width
    lineWidth = attr.ib(default=3)

    # TODO: active window
    # TODO: add new window off active

    def addFiles(self, filePaths):
        for path in filePaths:
            self.filePaths.append(path)
            nextTree = Tree() # TODO: add nextTree as child of prevTree
            self.trees.append(nextTree)
            self.uiStates.append(UIState(parent=self, tree=nextTree))

    def toggleLineWidth(self):
        if self.lineWidth == 4:
            self.lineWidth = 1
        else:
            self.lineWidth += 1

    def changeZAxis(self, delta):
        self.zAxisAt = snapToRange(self.zAxisAt + delta, 0, self.volumeSize[0] - 1)

    def updateVolumneSize(self, volumeSize):
        print(volumeSize)
        # TODO: Something better when volume sizes don't match? ...
        if self.volumeSize is None:
            self.volumeSize = volumeSize
