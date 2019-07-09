import attr

from pydynamo_brain.model import Point
from pydynamo_brain.util import deltaSz

class PunctaActions():
    DEFAULT_RADIUS_PX = 3 # default size in zoomed out pixels

    def __init__(self, fullState, history):
        self.state = fullState
        self.history = history

    # Get local UI state for this stack
    def _localState(self, localIdx):
        return self.state.uiStates[localIdx]

    # Create a new point
    def createPuncta(self, localIdx, location):
        self.history.pushState()
        localState = self._localState(localIdx)

        newID = localState.maybeCreateNewID(None)
        # First deselect in previous:
        for atIndex in range(localIdx):
            self.state.uiStates[atIndex].selectPunctaByID(None)

        # Add to this and all later:
        for atIndex in range(localIdx, len(self.state.uiStates)):
            while not atIndex < len(self.state.puncta):
                self.state.puncta.append([])
            self.state.puncta[atIndex].append(Point(
                id=newID,
                location=location,
                radius=self.DEFAULT_RADIUS_PX
            ))
            self.state.uiStates[atIndex].selectPunctaByID(newID)

    # Remove a point, and optionally the same point in later stacks:
    def removePoint(self, localIdx, targetPoint, laterStacks=False):
        self.history.pushState()
        targetID = targetPoint.id
        upperBound = len(self.state.puncta) if laterStacks else localIdx + 1
        for atIndex in range(localIdx, upperBound):
            if atIndex < len(self.state.puncta):
                # Filter out matching points
                self.state.puncta[atIndex] = [
                    point for point in self.state.puncta[atIndex] if point.id != targetID
                ]

    # Select a point, on this stack and all other stacks its on
    def selectPoint(self, localIdx, pointClicked):
        self.history.pushState()
        for uiState in self.state.uiStates:
            uiState.selectPunctaByID(pointClicked.id)

    # Select the next/previous point:
    def selectNextPoint(self, localIdx, delta):
        # Find the next point in this stack:
        if localIdx >= len(self.state.puncta):
            return
        punctaList = self.state.puncta[localIdx]

        localState = self._localState(localIdx)
        current = localState.currentPuncta()
        selectedIdx = -1
        for i, p in enumerate(punctaList):
            if p.id == current.id:
                selectedIdx = i
        if selectedIdx == -1:
            return
        nextIdx = (selectedIdx + delta) % len(punctaList)
        self.selectPoint(localIdx, punctaList[nextIdx])

    # Move the middle of a point, leaving radius the same.
    def movePointCenter(self, localIdx, location):
        self.history.pushState()
        localState = self._localState(localIdx)
        current = localState.currentPuncta()
        if current is not None:
            current.location = location

    # Move the middle of point, by a set amount
    def relativeMove(self, localIdx, dX, dY, laterStacks=False):
        localState = self._localState(localIdx)
        current = localState.currentPuncta()
        if current is not None:
            self.history.pushState()
            upperBound = len(self.state.puncta) if laterStacks else localIdx + 1
            for atIndex in range(localIdx, upperBound):
                current = self._localState(atIndex).currentPuncta()
                if current is not None:
                    current.location = (
                        current.location[0] + dX,
                        current.location[1] + dY,
                        current.location[2]
                    )

    # Change the radius of a point, leaving center the same.
    def movePointBoundary(self, index, location):
        localState = self._localState(index)
        current = localState.currentPuncta()
        if current is not None:
            self.history.pushState()
            current.radius = deltaSz(location, current.location)

    # Grow/shrink the radius of point, by a set ratio
    def relativeGrow(self, localIdx, dR, laterStacks=False):
        localState = self._localState(localIdx)
        current = localState.currentPuncta()
        if current is not None:
            self.history.pushState()
            upperBound = len(self.state.puncta) if laterStacks else localIdx + 1
            for atIndex in range(localIdx, upperBound):
                current = self._localState(atIndex).currentPuncta()
                if current is not None:
                    current.radius *= dR
