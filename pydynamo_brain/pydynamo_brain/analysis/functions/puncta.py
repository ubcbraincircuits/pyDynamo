import math
import numpy as np
import pandas as pd

from typing import Any, Dict, List
from tqdm import tqdm


import pydynamo_brain.util as util
from pydynamo_brain.model import FullState, Point

_IMG_CACHE = util.ImageCache()

# Given r, return pi.r^2, the area of a circle
def _radiusToArea(r: float) -> float:
    return math.pi * r * r

def _averageIntensity(point: Point, image: np.ndarray, channel: int) -> float:
    x, y, z = point.location
    zAt = int(round(z))
    plane = image[channel][zAt]

    r = point.radius
    if r is None:
        r = point.radiusFromAncestors()

    # HACK - find a better way to do this?
    intensitySum = 0.0
    intensityCount = 0
    for r in range(plane.shape[0]):
        for c in range(plane.shape[1]):
            d = util.deltaSz((c + 0.5, r + 0.5, 0), (x, y, 0))
            if d <= r:
                intensitySum += 1.0 * plane[r, c]
                intensityCount += 1
    if intensityCount == 0:
        return np.nan
    return intensitySum / intensityCount / 255.0

# Provide the size of each individual puncta across time.
def perPunctaSize(fullState: FullState, punctaIDs: List[str], **kwargs: Any) -> pd.DataFrame:
    idToIndex = {}
    for idx, id in enumerate(punctaIDs):
        idToIndex[id] = idx

    sizes = np.zeros((len(punctaIDs), len(fullState.puncta)))
    for idx, punctaList in enumerate(fullState.puncta):
        for puncta in punctaList:
            radius = puncta.radius
            if radius is None:
                radius = puncta.radiusFromAncestors()

            pID = puncta.id
            if pID in idToIndex:
                sizes[idToIndex[pID], idx] = _radiusToArea(radius)
    colNames = [('area_%02d' % (i + 1)) for i in range(len(fullState.puncta))]
    return pd.DataFrame(data=sizes, index=punctaIDs, columns=colNames)

# Provide the average intensity of puncta across time
def perPunctaIntensity(
    fullState: FullState, punctaIDs: List[str], **kwargs: Any
) -> pd.DataFrame:
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
