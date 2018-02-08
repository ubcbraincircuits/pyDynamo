import math
import numpy as np

SAVE_KEY = 'persist'
SAVE_META = {SAVE_KEY: True}

def snapToRange(x, lo, hi):
    return np.maximum(lo, np.minimum(hi, x))

def normDelta(p1, p2):
    x, y, z = p1[0] - p2[0], p1[1] - p2[1], p1[2] - p2[2]
    sz = math.sqrt(x*x + y*y + z*z)
    return (x/sz, y/sz, z/sz)

def dotDelta(p1, p2):
    return p1[0] * p2[0] + p1[1] * p2[1] + p1[2] * p2[2]

def deltaSz(p1, p2):
    x, y, z = p1[0] - p2[0], p1[1] - p2[1], p1[2] - p2[2]
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
