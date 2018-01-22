import attr

from .tree import *

@attr.s
class UIState():
    # Tree being shown in the UI.
    _tree = attr.ib(default=None)

    # Currently active branch, indexed by position in list of branches.
    currentBranchIndex = attr.ib(default=-1)

    # Currently active point, indexed by position in list of nodes.
    currentPointIndex = attr.ib(default=-1)

    # UI Option for whether or not to show annotations.
    showAnnotations = attr.ib(default=True)

    # UI Option for whether or not to show all branches, or just the nearby ones.
    drawAllBranches = attr.ib(default=False)

    def currentBranch(self):
        return self._tree.branches[self.currentBranchIndex]

    def currentPoint(self):
        if self.currentPointIndex == -1:
            return self._tree.rootPoint
        return self.currentBranch().points[self.currentPointIndex]

    def addPointToCurrentBranchAndSelect(self, location):
        if self._tree.rootPoint is None:
            self._tree.rootPoint = Point(location)
            return
        if self.currentBranchIndex == -1:
            self.currentBranchIndex = self._tree.addBranch(Branch(parentPoint=self._tree.rootPoint))
        self.currentPointIndex = self.currentBranch().addPoint(Point(location))

    def addPointToNewBranchAndSelect(self, location):
        if self.currentBranchIndex == -1:
            return
        # TODO - don't create a secondary branch as the first edge.
        newBranch = Branch(parentPoint=self.currentPoint())
        self.currentBranchIndex = self._tree.addBranch(newBranch)
        self.currentPointIndex = self.currentBranch().addPoint(Point(location))
