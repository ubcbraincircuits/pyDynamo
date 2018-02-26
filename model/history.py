import attr
import copy

from .tree import *
from .uiState import *
from .fullState import *

class History:
    # State singleton that is being modified by the app:
    liveState = None

    # List of previous state snapshots that can be undo'd to:
    undoStack = []

    # After undo, keep previous state in redo stack so undo can be undone
    redoStack = []

    def __init__(self, liveState):
        assert liveState is not None, "History must be created with non-None live state"
        self.liveState = liveState

    # Remember the current live state so we can go back to it later if needed.
    def pushState(self):
        stateSnapshot = self.deepClone(self.liveState)
        self.undoStack.append(stateSnapshot)
        self.redoStack = [] # Previous redo stack cleared on state push
        # print("History PUSH, #snapshots = (%d - %d)" % (len(self.undoStack), len(self.redoStack)))
        return stateSnapshot

    def undo(self):
        if len(self.undoStack) == 0:
            return False # Cannot undo with nothing to undo back to.
        self.redoStack.append(self.deepClone(self.liveState))
        self.copyInto(self.undoStack.pop(), self.liveState)
        # print("History UNDO, #snapshots = (%d - %d)" % (len(self.undoStack), len(self.redoStack)))
        return True

    def redo(self):
        if len(self.redoStack) == 0:
            return False # Cannot redo with nothing to redo back insertPointBefore
        self.undoStack.append(self.deepClone(self.liveState))
        self.copyInto(self.redoStack.pop(), self.liveState)
        # print("History REDO, #snapshots = (%d - %d)" % (len(self.undoStack), len(self.redoStack)))
        return True

    def deepClone(self, modelToClone):
        return copy.deepcopy(modelToClone)

    def copyInto(self, modelFrom, modelTo):
        for field in attr.fields(modelFrom.__class__):
            setattr(modelTo, field.name, getattr(modelFrom, field.name))
