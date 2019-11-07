# Given a volume, and a tree in it, make everything away from the tree darker.
import numpy as np
import scipy.ndimage as ndimage

MIN_DIST_TREE_UM = 5
MAX_DIST_TREE_UM = 10

MIN_DIST_SOMA_UM = 12
MAX_DIST_SOMA_UM = 20


# https://www.geeksforgeeks.org/bresenhams-algorithm-for-3-d-line-drawing/
# Python3 code for generating points on a 3-D line using Bresenham's Algorithm
def Bresenham3D(x1, y1, z1, x2, y2, z2):
    points = [(x1, y1, z1)]
    dx, dy, dz = abs(x2 - x1), abs(y2 - y1), abs(z2 - z1)
    xs = 1 if (x2 > x1) else -1
    ys = 1 if (y2 > y1) else -1
    zs = 1 if (z2 > z1) else -1

    # Driving axis is X-axis
    if (dx >= dy and dx >= dz):
        p1, p2 = 2 * dy - dx, 2 * dz - dx
        while (x1 != x2):
            x1 += xs
            if (p1 >= 0):
                y1, p1 = y1 + ys, p1 - 2 * dx
            if (p2 >= 0):
                z1, p1 = z1 + zs, p2 - 2 * dx
            p1, p2 = p1 + 2 * dy, p2 + 2 * dz
            points.append((x1, y1, z1))
        return points

    # Driving axis is Y-axis
    if (dy >= dx and dy >= dz):
        p1, p2 = 2 * dx - dy, 2 * dz - dy
        while (y1 != y2):
            y1 += ys
            if (p1 >= 0):
                x1, p1 = x1 + xs, p1 - 2 * dy
            if (p2 >= 0):
                z1, p2 = z1 + zs, p2 - 2 * dy
            p1, p2 = p1 + 2 * dx, p2 + 2 * dz
            points.append((x1, y1, z1))
        return points

    # Driving axis is Z-axis
    p1, p2 = 2 * dy - dz, 2 * dx - dz
    while (z1 != z2):
        z1 += zs
        if (p1 >= 0):
            y1, p1 = y1 + ys, p1 - 2 * dz
        if (p2 >= 0):
            x1, p2 = x1 + xs, p2 - 2 * dz
        p1, p2 = p1 + 2 * dy, p2 + 2 * dx
        points.append((x1, y1, z1))
    return points

def _ZMaxLastChannel(volume):
    v = volume[..., -1] if len(volume.shape) == 4 else volume
    return np.max(v, axis=0)

def _drawLineInto(result, pA, pB):
    allPoints = Bresenham3D(
        round(pA[0]), round(pA[1]), round(pA[2]),
        round(pB[0]), round(pB[1]), round(pB[2])
    )
    for (x, y, z) in allPoints:
        if 0 <= z < result.shape[1] and 0 <= x < result.shape[2] and 0 <= y < result.shape[3]:
            result[:, z, y, x] = 0

def _drawBranchInto(result, branch):
    lastAt = branch.parentPoint.location
    for point in branch.points:
        nextAt = point.location
        _drawLineInto(result, lastAt, nextAt)
        lastAt = nextAt

# Fill 0s for tree lines, 1 elsewhere:
def tree01(tree, shape):
    assert len(shape) == 4
    result = np.ones(shape)
    for branch in tree.branches:
        _drawBranchInto(result, branch)
    return result

def soma01(tree, shape):
    result = np.ones(shape)
    somaAt = tree.rootPoint.location
    x, y, z = round(somaAt[0]), round(somaAt[1]), round(somaAt[2])
    assert len(shape) == 4
    result[:, z, y, x] = 0
    return result

def linearClip(volume, minV, maxV):
    return (np.clip(volume, minV, maxV) - minV) / (maxV - minV)

# Shape = CZXY
def volumeNearTree(tree, shape, xyzScale=None, exponent=3):
    assert len(shape) == 4 and len(xyzScale) == 3
    if xyzScale is not None:
        HUGE_SCALE = 10000
        czxyScale = [HUGE_SCALE, xyzScale[2], xyzScale[0], xyzScale[1]] # CZXY

    print ("...Distance from tree transform...")
    treeDist = ndimage.distance_transform_edt(tree01(tree, shape), sampling=czxyScale)
    print ("...change to clipped distance...\n")
    treeClip = linearClip(treeDist, MIN_DIST_TREE_UM, MAX_DIST_TREE_UM)
    treeClip = 1 - np.power(treeClip, exponent)

    print ("...Distance from soma transform...")
    somaDist = ndimage.distance_transform_edt(soma01(tree, shape), sampling=czxyScale)
    print ("...change to clipped distance...\n")
    somaClip = linearClip(somaDist, MIN_DIST_SOMA_UM, MAX_DIST_SOMA_UM)
    somaClip = 1 - np.power(somaClip, exponent)

    print ("...merge...")
    return np.maximum(treeClip, somaClip)

def maskedNearTree(initialVolume, tree, xyzScale, exponent=3):
    nearTree = volumeNearTree(tree, initialVolume.shape, xyzScale, exponent)
    return initialVolume * nearTree
