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

    # TODO: active window
    # TODO: add new window off active

    def addFiles(self, filePaths):
        for path in filePaths:
            self.filePaths.append(path)
            nextTree = Tree() # TODO: add nextTree as child of prevTree
            self.trees.append(nextTree)
            self.uiStates.append(UIState(tree=nextTree))
