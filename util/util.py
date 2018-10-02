import math
import numpy as np
import time
import os.path

SAVE_KEY = 'persist'
SAVE_META = {SAVE_KEY: True}

def currentTimeMillis():
    return int(round(time.time() * 1000))

def snapToRange(x, lo, hi):
    return np.maximum(lo, np.minimum(hi, x))

# Given two tuples A = (Ax, Ay, Az), B = (Bx, By, Bz), return A + B
def locationPlus(A, B):
    return (A[0] + B[0], A[1] + B[1], A[2] + B[2])

# Given two tuples A = (Ax, Ay, Az), B = (Bx, By, Bz), return A - B
def locationMinus(A, B):
    return (A[0] - B[0], A[1] - B[1], A[2] - B[2])

def normDelta(p1, p2):
    x, y, z = locationMinus(p1, p2)
    sz = math.sqrt(x*x + y*y + z*z)
    return (x/sz, y/sz, z/sz)

def dotDelta(p1, p2):
    return p1[0] * p2[0] + p1[1] * p2[1] + p1[2] * p2[2]

def deltaSz(p1, p2):
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

# Utility for nicer formatting of the window, using index and just image file name.
def createTitle(index, path):
    return "[%d] - %s" % (index + 1, os.path.basename(path))

# Read the zAxis to show from a uiState
def zStackForUiState(uiState):
    # Left here to support the future possibility of making all Z the same,
    # rather than relative to the selected point.
    return uiState.zAxisAt
