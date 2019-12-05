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

    def radiusFromIntensity(self, fullState, volume, point):
        zIdx = round(point.location[2])
        if point.isRoot():

            plane = volume[fullState.channel, zIdx, :, :]
            # Detect edges and apply a gaussian_filter blur
            modifiedPlane = roberts(plane)
            modifiedPlane = ndimage.gaussian_filter(modifiedPlane, sigma=3)
            # Use Canny edge dectection edges
            edges = feature.canny(plane, sigma=2)
            edges[edges == 0] = np.nan
            modifiedPlane = edges * modifiedPlane

        else:
            loIdx, hiIdx = max(0, zIdx - 1), min(volume.shape[1], zIdx + 2)
            plane = volume[fullState.channel, loIdx:hiIdx, :, :]
            plane = np.amax(plane, axis=0)
            # Detect edges and apply a gaussian_filter blur
            modifiedPlane = roberts(plane)
            modifiedPlane = ndimage.gaussian_filter(modifiedPlane, sigma=3)
            # Use Canny edge dectection edges
            edges = feature.canny(plane, sigma=2)
            # Subtract Canny edges from gaussion blur
            # Find branch edges near the crossover point in array instensity
            modifiedPlane = modifiedPlane - edges

        plane01 = np.ones(plane.shape)
        plane01[int(point.location[1]), int(point.location[0])] = 0
        planeDist = ndimage.distance_transform_edt(plane01)

        X_POINTS = 100 #Number of points 'X' sampled
        SQUISH = 1 #Power of the skewed of the distrubtion
        MAX_DIST_PX = 30 #Max distance sampled away from the the point in pixels

        xs = 1 + np.power(np.arange(0, 1, 1 / X_POINTS), SQUISH) * (MAX_DIST_PX - 1)
        ys = []
        for x in xs:
            selected = (planeDist < x)
            ys.append(np.mean(modifiedPlane[selected]))

        if point.isRoot():
            # Max instensity
            index = ys.index(np.max(ys))
            radius = xs[index]
        else:
            # Select for radius where instensity == threshold 0.0
            for i, x in enumerate(xs):
                if ys[i] <= 0.0:
                    radius = xs[i]
                    break

        #prevent terminal points from having a radius larger than their parent
        if point.isLastInBranch() and (not point.isRoot()):
            prevPoint = point.nextPointInBranch(delta=-1)
            if prevPoint is not None:
                parentRadius = prevPoint.radius
                if parentRadius is None:
                    parentRadius = 1
                if radius is None:
                        radius = 1
                if radius >= parentRadius * 2:
                    radius = parentRadius
        return radius

    def radiiEstimator(self, fullState, id, point, recursive=False):
        volume = _IMG_CACHE.getVolume(fullState.uiStates[id].imagePath)
        points = point.flattenSubtreePoints() if recursive else [point]
        for p in points:
            radius = self.radiusFromIntensity(fullState, volume, p)
            p.radius = radius
            p.manuallyMarked = True

    #Function to edit radius of selected point by clicking
    def editRadiiOnClick(self, location, uiState, zFilter=True):
        self.history.pushState()
        mouseX, mouseY, mouseZ = location
        point = uiState.currentPoint()
        pointX, pointY, pointZ = point.location

        if round(mouseZ) == round(pointZ):
            newRadius = math.sqrt(math.pow((mouseX-pointX),2)+math.pow((mouseY-pointY),2))
            point.radius = newRadius
            point.manuallyMarked = False

        return
