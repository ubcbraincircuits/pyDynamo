import attr

@attr.s
class Point():
    # Node position as an (x, y, z) tuple.
    location = attr.ib(default=None) # (x, y, z) tuple

    # Text annotation for node.
    annotation = attr.ib(default="")

    # Branches coming off the node
    children = attr.ib(default=[]) # Not used yet

    # Not sure...?
    hilighed = attr.ib(default=None) # Not used yet


@attr.s
class Branch():
    # Points along this dendrite branch, in order.
    points = attr.ib(default=[])

    # Not sure...?
    isEnded = attr.ib(default=False) # Not used yet

    # Not sure...?
    colorData = attr.ib(default=None) # Not used yet

    def addPoint(self, point):
        self.points.append(point)
        return len(self.points) - 1

@attr.s
class Tree():
    # All branches making up this dendrite tree.
    branches = attr.ib(default=[])

    def addBranch(self, branch):
        self.branches.append(branch)
        return len(self.branches) - 1
