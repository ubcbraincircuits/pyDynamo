import math
import numpy as np
import scipy
import time
import os.path

from typing import Dict, Tuple

# Type aliases for points
Point3D = Tuple[float, float, float]

SAVE_KEY = 'persist'
SAVE_META: Dict[str, bool] = {SAVE_KEY: True}

# Function that does nothing:
NOOP_FUNC = lambda: None

def currentTimeMillis():
    return int(round(time.time() * 1000))

def snapToRange(x, lo, hi):
    return np.maximum(lo, np.minimum(hi, x))

# Given two tuples A = (Ax, Ay, Az), B = (Bx, By, Bz), return A + B
def locationPlus(A: Point3D, B: Point3D) -> Point3D:
    return (A[0] + B[0], A[1] + B[1], A[2] + B[2])

# Given two tuples A = (Ax, Ay, Az), B = (Bx, By, Bz), return A - B
def locationMinus(A: Point3D, B: Point3D) -> Point3D:
    return (A[0] - B[0], A[1] - B[1], A[2] - B[2])

def normDelta(p1, p2):
    x, y, z = locationMinus(p1, p2)
    sz = math.sqrt(x*x + y*y + z*z)
    return (x/sz, y/sz, z/sz)

def dotDelta(p1, p2):
    return p1[0] * p2[0] + p1[1] * p2[1] + p1[2] * p2[2]

def deltaSz(p1: Point3D, p2: Point3D) -> float:
    x, y, z = locationMinus(p1, p2)
    return math.sqrt(x*x + y*y + z*z)

# TODO - remove
def rotation_matrix(axis, theta):
    """
    Return the rotation matrix associated with counterclockwise rotation about
    the given axis by theta radians.
    """
    axis = np.asarray(axis)
    axis = axis/math.sqrt(np.dot(axis, axis))
    a = math.cos(theta/2.0)
    b, c, d = -axis*math.sin(theta/2.0)
    aa, bb, cc, dd = a*a, b*b, c*c, d*d
    bc, ad, ac, ab, bd, cd = b*c, a*d, a*c, a*b, b*d, c*d
    return np.array([[aa+bb-cc-dd, 2*(bc+ad), 2*(bd-ac)],
                     [2*(bc-ad), aa+cc-bb-dd, 2*(cd+ab)],
                     [2*(bd+ac), 2*(cd-ab), aa+dd-bb-cc]])

def emptyArrayArray(c):
    d = []
    for i in range(c):
        d.append([])
    return d

def emptyArrayMatrix(r, c):
    d = []
    for i in range(r):
        d.append(emptyArrayArray(c))
    return d

def lastPointWithLabelIdx(points, label):
    lastPointIdx = -1
    for i, point in enumerate(points):
        if point.annotation.find(label) != -1:
            lastPointIdx = i
    return lastPointIdx

# Sorted list of all branch IDs found in the given list of trees.
def sortedBranchIDList(trees):
    ids = set()
    for tree in trees:
        ids |= set([b.id for b in tree.branches])
    return sorted(list(ids))

# Sorted list of all puncta IDs found in the given list of trees.
def sortedPunctaIDList(punctaLists):
    ids = set()
    for punctaList in punctaLists:
        ids |= set([p.id for p in punctaList])
    return sorted(list(ids))

# Utility for nicer formatting of the window, using index and just image file name.
def createTitle(index, path):
    return "[%d] - %s" % (index + 1, os.path.basename(path))

# Read the zAxis to show from a uiState
def zStackForUiState(uiState):
    # Left here to support the future possibility of making all Z the same,
    # rather than relative to the selected point.
    return uiState.zAxisAt

# Return a new list, same as the old one except skipping one index
def listWithoutIdx(data, index):
    return [v for i, v in enumerate(data) if i != index]

# Move an item from one location in a list to another, in place
def moveInList(data, indexFrom, indexTo):
    n = len(data)
    assert (0 <= indexFrom < n) and (0 <= indexTo < n)
    data.insert(indexTo, data.pop(indexFrom))

def douglasPeucker(PointList, epsilon):
    """Returns reduced points list using the Ramer–Douglas–Peucker algorithm

        Inputs:
        PointList: list of (x,y) tuples
        epsilon
    """
    
    pointArray = np.array(PointList)
    dmax =0
    index = 0
    end = pointArray.shape[0]

    p1=np.array(pointArray[0])
    p2=np.array(pointArray[-1])

    for i in range(0, end, 2):
        p3 = np.array(pointArray[i])
        d  = abs(np.cross(p2-p1,p3-p1)/np.linalg.norm(p2-p1))
        if d > dmax:
            index = i
            dmax = d

    results = []
    if dmax > epsilon:
        recResults1 = douglasPeucker(pointArray[:index], epsilon)
        recResults2 = douglasPeucker(pointArray[index:end], epsilon)
        results.extend(recResults1)
        results.extend(recResults2)
    else:
        results = [(p1[0], p1[1]), (p2[0], p2[1])]

    return results
