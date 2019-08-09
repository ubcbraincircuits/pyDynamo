import numpy as np
import numpy.polynomial.polynomial as npPoly

from numpy.linalg import det, norm

# Smooth to a polynomial of degree 7:
_DEFAULT_POLY_DEGREE = 7

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
def shollCrossings(tree, binSizeUm, maxRadius):
    radii = np.arange(0, maxRadius, binSizeUm)
    crossCounts = [_nCrossings(tree, r) for r in radii]
    return np.array(crossCounts), radii

# Calculate metrics from fitting a curve to the crossings:
def shollMetrics(crossCounts, radii, polyDegree=_DEFAULT_POLY_DEGREE):
    bounds = [np.min(radii), np.max(radii)]

    # Fit to polynomial...
    pCoeff = npPoly.polyfit(radii, crossCounts, polyDegree)

    # ...then find max value, happens at a critical point:
    roots = npPoly.polyroots(npPoly.polyder(pCoeff))
    critX = bounds + [r.real for r in roots if bounds[0] <= r.real <= bounds[1]]
    critY = npPoly.polyval(critX, pCoeff)
    maxYIdx = np.argmax(critY)
    maxX, maxY = critX[maxYIdx], critY[maxYIdx]

    return pCoeff, maxX, maxY
