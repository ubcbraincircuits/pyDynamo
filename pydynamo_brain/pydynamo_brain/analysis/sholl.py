import numpy as np
from numpy.linalg import det, norm

# from: https://gist.github.com/nim65s/5e9902cd67f094ce65b0
def _distance(A, B, P):
    """ segment line AB, point P, where each one is an array([x, y]) """
    if np.all(A == P) or np.all(B == P):
        return 0
    if np.arccos(np.dot((P - A) / norm(P - A), (B - A) / norm(B - A))) > np.pi / 2:
        return norm(P - A)
    if np.arccos(np.dot((P - B) / norm(P - B), (A - B) / norm(A - B))) > np.pi / 2:
        return norm(P - B)
    return norm(np.cross(A - B, A - P)) / norm(B - A)

def _lineSegmentCrossRadius(tree, fr, to, soma, r):
    xs, ys, zs = tree.worldCoordPoints([fr, to, soma])
    A = np.array([xs[0], ys[0], zs[0]])
    B = np.array([xs[1], ys[1], zs[1]])
    P = np.array([xs[2], ys[2], zs[2]])
    maxDist = max(norm(P - A), norm(P - B))
    minDist = _distance(A, B, P)
    return minDist <= r <= maxDist

# Number of times branches of the tree cross a given radius
def _nCrossings(tree, rad):
    crosses = 0
    for point in tree.flattenPoints():
        if point.isRoot():
            continue
        pointBefore = point.nextPointInBranch(delta=-1, noWrap=False)
        if _lineSegmentCrossRadius(tree, point, pointBefore, tree.rootPoint, rad):
            crosses += 1
    return crosses

# Calculate sholl properties for a tree
def shollCrossings(tree, binSizeUm, maxRadius, in2D=False):
    radii = np.arange(0, maxRadius, binSizeUm)
    crossCounts = [_nCrossings(tree, r) for r in radii]
    return np.array(crossCounts), radii
