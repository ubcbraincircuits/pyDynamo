import attr

@attr.s
class Point():
    # Node position as an (x, y, z) tuple.
    location = attr.ib(default=None) # (x, y, z) tuple

    # Text annotation for node.
    annotation = attr.ib(default="")

    # Branches coming off the node
    children = attr.ib(default=attr.Factory(list)) # Not used yet

    # Not sure...?
    hilighed = attr.ib(default=None) # Not used yet


@attr.s
class Branch():
    # Node this branched off, or None for root branch
    parentPoint = attr.ib(default=None)

    # Points along this dendrite branch, in order.
    points = attr.ib(default=attr.Factory(list))

    # Not sure...?
    isEnded = attr.ib(default=False) # Not used yet

    # Not sure...?
    colorData = attr.ib(default=None) # Not used yet

    def addPoint(self, point):
        self.points.append(point)
        return len(self.points) - 1

@attr.s
class Tree():
    # Soma, initial start of the main branch.
    rootPoint = None

    # All branches making up this dendrite tree.
    branches = attr.ib(default=attr.Factory(list))

    def addBranch(self, branch):
        self.branches.append(branch)
        return len(self.branches) - 1

    def flattenPoints(self):
        if self.rootPoint is None:
            return []
        result = [self.rootPoint]
        for branch in self.branches:
            result.extend(branch.points)
        return result


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
