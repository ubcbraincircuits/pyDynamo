import attr

@attr.s
class Branch():
    branchID = attr.ib()

    points = attr.ib(default=[]) # matlab {1}
    children = attr.ib(default=[]) # matlab {2}
    annotation = attr.ib(default=[]) # matlab {3}
    hilighted = attr.ib(default=[]) # matlab {4}

    isEnded = attr.ib(default=False)
    colorData = attr.ib(default=None)

    def addPoint(self, point):
        self.points.append(point)
        self.children.append([])
        self.annotation.append('')
        self.hilighted.append(0)
        self.isEnded = False
        self.colorData = None # hmm...

@attr.s
class Tree():
    branches = attr.ib(default=[Branch(branchID=0)])
    currentBranch = attr.ib(default=0)

    def getCurrentBranch(self):
        return self.branches[self.currentBranch]

    def addPoint(self, point):
        self.getCurrentBranch().addPoint(point)
