import math
import numpy as np

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
