import attr
import numpy as np
import skimage
import math

from scipy.interpolate import interp1d
from scipy import ndimage
from skimage import feature
from skimage.filters import roberts
from skimage.measure import profile_line

from pydynamo_brain.model import Point
import pydynamo_brain.util as util

_IMG_CACHE = util.ImageCache()

class RadiiActions():
    DEFAULT_RADIUS_PX = 3 # default size in zoomed out pixels

    def __init__(self, fullState, history):
        self.state = fullState
        self.history = history

    # Get local UI state for this stack
    def _localState(self, localIdx):
        return self.state.uiStates[localIdx]

    # Grow/shrink the radius of a point, by a set ratio
    def changeRadius(self, localIdx, dR, laterStacks=False):
        localState = self._localState(localIdx)
        sourcePoint = self.state.uiStates[localIdx].currentPoint()
        if sourcePoint is not None:
            self.history.pushState()
            upperBound = len(self.state.uiStates) if laterStacks else localIdx + 1
            for atIndex in range(localIdx, upperBound):
                current = self._localState(atIndex).currentPoint()
                if current is not None:
                    current.manuallyMarked = False
                    if current.radius == None:
                        current.radius = 10 * dR
                    else:
                        current.radius *= dR


def _radiiThreshold(xs, ys):
    PADDING = 10
    for i, x in enumerate(xs):
        if ys[i] <= 0.0:
            return xs[i]

def _somaThreshold(xs, ys):
    PADDING = 10
    index = ys.index(np.max(ys))
    return xs[index]

def intensityForPointRadius(volume, point):
    zIdx = int(point.location[2])
    plane = volume[0, (zIdx-1):(zIdx+1), :, :]
    if point.isRoot:
        plane = volume[0, zIdx, :, :]
        planeMod = roberts(plane)
        planeMod = ndimage.gaussian_filter(planeMod, sigma=3)
        edges = feature.canny(plane, sigma=2)
        edges[edges == 0]= np.nan
        planeMod = edges * planeMod
    else:
        plane = np.amax(plane, axis=0)
        planeMod = roberts(plane)
        planeMod = ndimage.gaussian_filter(planeMod, sigma=3)
        edges = feature.canny(plane, sigma=2)
        planeMod = planeMod - edges

    plane01 = np.ones(plane.shape)
    plane01[int(point.location[1]), int(point.location[0])] = 0
    planeDist = ndimage.distance_transform_edt(plane01)

    _mx = np.max(planeDist)
    planeDistNorm = np.power(((_mx - planeDist) / _mx), 13)

    X_POINTS = 100
    SQUISH = 1
    MAX_DIST_PX = 30

    xs = 1 + np.power(np.arange(0, 1, 1 / X_POINTS), SQUISH) * (MAX_DIST_PX - 1)
    ys = []
    for x in xs:
        selected = (planeDist < x)
        ys.append(np.mean(planeMod[selected]))

    radius = point.radius
    if point.isRoot:
        radius = _somaThreshold(xs, ys)
    else:
        radius = _radiiThreshold(xs, ys)
    if radius == None:
        radius = 1

    #prevent terminal points from having a radius lareger than their parents
    if point.isLastInBranch() and (point.isRoot()==False):
        parentPoint = point.pathFromRoot()[-2]
        if parentPoint.radius!=None:
            parentRadius = parentPoint.radius
            if radius >= parentRadius:
                radius = parentRadius
    return radius

def singleRadiusEstimation(fullState, id, point):
    newTree = fullState.uiStates[id]._tree
    volume = _IMG_CACHE.getVolume(fullState.uiStates[id].imagePath)
    radius = intensityForPointRadius(volume, point)
    point.radius = radius
    point.manuallyMarked = True

    return

def recursiveRadiiEstimator(fullState, id, branch, point):
    newTree = fullState.uiStates[id]._tree
    volume = _IMG_CACHE.getVolume(fullState.uiStates[id].imagePath)

    childrenPoints = point.flattenSubtreePoints()
    for p in childrenPoints:
        radius = intensityForPointRadius(volume, p)
        p.radius = radius
        p.manuallyMarked = True

    return
