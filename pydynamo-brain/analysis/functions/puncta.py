import math
import numpy as np
import pandas as pd

from tqdm import tqdm

# hack
import matplotlib.pyplot as plt

import util

_IMG_CACHE = util.ImageCache()

# Given r, return pi.r^2, the area of a circle
def _radiusToArea(r):
    return math.pi * r * r

def _averageIntensity(point, image, channel):
    x, y, z = point.location
    zAt = int(round(z))
    plane = image[channel][zAt]

    # HACK - find a better way to do this?
    intensitySum = 0.0
    intensityCount = 0
    for r in range(plane.shape[0]):
        for c in range(plane.shape[1]):
            d = util.deltaSz((c + 0.5, r + 0.5, 0), (x, y, 0))
            if d <= point.radius:
                intensitySum += 1.0 * plane[r, c]
                intensityCount += 1
    if intensityCount == 0:
        return np.nan
    return intensitySum / intensityCount / 255.0

"""
TODO - add back if wanted? Or migrate to tree functions?
# Provide the number of puncta drawn in each tree.
def punctaCount(fullState, **kwargs):
    counts = []
    for i in range(len(fullState.trees)):
        if i < len(fullState.puncta):
            counts.append(len(fullState.puncta[i]))
        else:
            counts.append(0)
    return pd.DataFrame({'punctaCount': counts})

# Provide the size of the puncta in each tree.
def totalPunctaSize(fullState, **kwargs):
    totalSizes = []
    for i in range(len(fullState.trees)):
        if i < len(fullState.puncta):
            totalSize = 0
            for p in fullState.puncta[i]:
                totalSize += _radiusToArea(p.radius)
            totalSizes.append(totalSize)
        else:
            totalSizes.append(0)
    return pd.DataFrame({'totalPunctaSize': totalSizes})

# Provide the average intensity of the puncta in each tree.
def totalPunctaIntensity(fullState, **kwargs):
    raise Exception("Coming soon: Puncta intensity analysis")
"""

# Provide the size of each individual puncta across time.
def perPunctaSize(fullState, punctaIDs, **kwargs):
    idToIndex = {}
    for idx, id in enumerate(punctaIDs):
        idToIndex[id] = idx

    sizes = np.zeros((len(punctaIDs), len(fullState.puncta)))
    for idx, punctaList in enumerate(fullState.puncta):
        for puncta in punctaList:
            pID = puncta.id
            if pID in idToIndex:
                sizes[idToIndex[pID], idx] = _radiusToArea(puncta.radius)
    colNames = [('area_%02d' % (i + 1)) for i in range(len(fullState.puncta))]
    return pd.DataFrame(data=sizes, index=punctaIDs, columns=colNames)

# Provide the average intensity of puncta across time
def perPunctaIntensity(fullState, punctaIDs, **kwargs):
    print ("Pre-loading images...")
    for imgPath in tqdm(fullState.filePaths):
        _IMG_CACHE.getVolume(imgPath, verbose=False)
    print ("Loaded")

    channel = 0
    if 'channel' in kwargs:
        channel = kwargs['channel']

    idToIndex = {}
    for idx, id in enumerate(punctaIDs):
        idToIndex[id] = idx

    intensities = np.zeros((len(punctaIDs), len(fullState.puncta)))
    for idx, punctaList in enumerate(fullState.puncta):
        assert idx < len(fullState.filePaths)
        img = _IMG_CACHE.getVolume(fullState.filePaths[idx], verbose=False)
        for puncta in punctaList:
            pID = puncta.id
            if pID in idToIndex:
                intensities[idToIndex[pID], idx] = _averageIntensity(puncta, img, channel)
    colNames = [('intensity_%02d' % (i + 1)) for i in range(len(fullState.puncta))]
    return pd.DataFrame(data=intensities, index=punctaIDs, columns=colNames)
