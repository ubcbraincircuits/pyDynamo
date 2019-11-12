import attr

from pydynamo_brain.model import Point
from pydynamo_brain.util import deltaSz

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
                    if current.radius == None:
                        current.radius = 10 * dR
                    else:
                        current.radius *= dR
