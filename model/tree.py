import attr
import util

@attr.s
class Point():
    # Node position as an (x, y, z) tuple.
    location = attr.ib(default=None) # (x, y, z) tuple

    # Branch this point belongs to
    parentBranch = attr.ib(default=None, repr=False, cmp=False)

    # Text annotation for node.
    annotation = attr.ib(default="", cmp=False)

    # Branches coming off the node
    children = attr.ib(default=attr.Factory(list)) # Not used yet

    # Not sure...?
    hilighted = attr.ib(default=None, cmp=False) # Not used yet


@attr.s
class Branch():
    # TODO: Tree this branch belongs to

    # Node this branched off, or None for root branch
    parentPoint = attr.ib(default=None, repr=False, cmp=False)

    # Points along this dendrite branch, in order.
    points = attr.ib(default=attr.Factory(list))

    # Not sure...?
    isEnded = attr.ib(default=False, cmp=False) # Not used yet

    # Not sure...?
    colorData = attr.ib(default=None, cmp=False) # Not used yet

    def addPoint(self, point):
        self.points.append(point)
        point.parentBranch = self
        return len(self.points) - 1

    def insertPointBefore(self, point, index):
        self.points.insert(index, point)
        point.parentBranch = self
        return index

    def removePointLocally(self, point):
        if point not in self.points:
            print ("Deleting point not in the branch? Whoops")
            return
        index = self.points.index(point)
        self.points.remove(point)
        return self.parentPoint if index == 0 else self.points[index - 1]

@attr.s
class Tree():
    # Soma, initial start of the main branch.
    rootPoint = attr.ib(default=None)

    # All branches making up this dendrite tree.
    branches = attr.ib(default=attr.Factory(list))

    def addBranch(self, branch):
        self.branches.append(branch)
        return len(self.branches) - 1

    def removeBranch(self, branch):
        if branch not in self.branches:
            print ("Deleting branch not in the tree? Whoops")
            return
        if len(branch.points) > 0:
            print ("Removing a branch that still has stuff on it? use uiState.removeBranch.")
            return
        self.branches.remove(branch)

    def flattenPoints(self):
        if self.rootPoint is None:
            return []
        result = [self.rootPoint]
        for branch in self.branches:
            result.extend(branch.points)
        return result

    def closestPointTo(self, targetLocation):
        closestDist, closestPoint = None, None
        for point in self.flattenPoints():
            dist = util.deltaSz(targetLocation, point.location)
            if closestDist is None or dist < closestDist:
                closestDist, closestPoint = dist, point
        return closestPoint

#
# Debug formatting for converting trees to string representation
#
def printPoint(tree, point, pad="", isFirst=False):
    print (pad + ("-> " if isFirst else "   ") + str(point))
    pad = pad + "   "
    for branch in tree.branches:
        if branch.parentPoint == point:
            printBranch(tree, branch, pad)

def printBranch(tree, branch, pad=""):
    if branch.points[0] == branch.parentPoint:
        print ("BRANCH IS OWN PARENT? :(")
        return
    isFirst = True
    for point in branch.points:
        printPoint(tree, point, pad, isFirst)
        isFirst = False

def printTree(tree):
    printPoint(tree, tree.rootPoint)
