import numpy as np

from pydynamo_brain.analysis import shollCrossings, shollMetrics
from pydynamo_brain.model import *

_NEXT_ID = 0
def _id():
    global _NEXT_ID
    _NEXT_ID += 1
    return '%d' % _NEXT_ID

def _buildBranch(parent, pointLocs):
    b = Branch(id=_id())
    for loc in pointLocs:
        b.addPoint(Point(id=_id(), location=loc))
    b.setParentPoint(parent)
    return b

# Single branch, (0, 0) to (5, 5)
def _treeOneLine():
    t = Tree()
    t.rootPoint = Point(id=_id(), location=(0, 0, 1))
    b1 = _buildBranch(t.rootPoint, [(1, 1, 1), (2, 2, 1), (3, 3, 1), (4, 4, 1), (5, 5, 1)])
    t.addBranch(b1)
    t._parentState = UIState()
    t._parentState._parent = FullState()
    t._parentState._parent.projectOptions.pixelSizes = [1, 1, 1]
    return t

# Forking branches
def _treeTripleFork():
    t = Tree()
    t.rootPoint = Point(id=_id(), location=(0, 0, 0))
    bX = _buildBranch(t.rootPoint, [(1, 0, 0), (2, 0, 0)])
    bY = _buildBranch(t.rootPoint, [(0, 1, 0), (0, 2, 0)])
    bZ = _buildBranch(t.rootPoint, [(0, 0, 1), (0, 0, 2)])
    t.addBranch(bX)
    t.addBranch(_buildBranch(bX.points[0], [(1, 1, 0)]))
    t.addBranch(_buildBranch(bX.points[0], [(1, 0, 1)]))
    t.addBranch(bY)
    t.addBranch(_buildBranch(bY.points[0], [(1, 1, 0)]))
    t.addBranch(_buildBranch(bY.points[0], [(0, 1, 1)]))
    t.addBranch(bZ)
    t.addBranch(_buildBranch(bZ.points[0], [(1, 0, 1)]))
    t.addBranch(_buildBranch(bZ.points[0], [(0, 1, 1)]))
    t._parentState = UIState()
    t._parentState._parent = FullState()
    t._parentState._parent.projectOptions.pixelSizes = [0.5, 0.5, 0.5]
    return t


def _checkMatch(a, b, msg=""):
    assert np.all(np.abs(a - b) < 1e-9), msg

def testCounts():
    tree = _treeOneLine()
    crossings, radii = shollCrossings(tree, 1.0, 10.0)
    # Single branch, (0, 0) to (5, 5) = 7.07 long
    #                                0  1  2  3  4  5  6  7  8  9
    _checkMatch(crossings, np.array([1, 1, 1, 1, 1, 1, 1, 1, 0, 0]))
    _checkMatch(radii, np.arange(0, 10, 1.0))

    # More complex forking in all axes
    tree = _treeTripleFork()
    crossings, radii = shollCrossings(tree, 0.1, 1.2)
    _checkMatch(crossings, np.array([3, 3, 3, 3, 3, 12, 9, 9, 3, 3, 3, 0]))
    _checkMatch(radii, np.arange(0, 1.2, 0.1))

def testMetrics():
    tree = _treeOneLine()
    pCoeff, maxX, maxY = shollMetrics(*shollCrossings(tree, 1.0, 8.0), polyDegree=1)
    _checkMatch(np.array([1, 0]), pCoeff)
    _checkMatch(np.array([0, 1]), np.array([maxX, maxY]))

    tree = _treeTripleFork()
    pCoeff, maxX, maxY = shollMetrics(*shollCrossings(tree, 1.0, 8.0))
    # X is around the middle, where there's 5(ish) smoothed crossings
    GOLDEN = np.array([0.38213415245437554, 5.156199457446908])
    _checkMatch(GOLDEN, np.array([maxX, maxY]))

def run():
    testCounts()
    testMetrics()
    return True

if __name__ == '__main__':
    run()
