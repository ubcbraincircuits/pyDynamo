import attr
import copy

from typing import List

from .fullState import FullState
from .tree.tree import Tree

class History:
    """Respresents the current live active state of the app, as well as a history of changes.
    After snapshotting with pushState(), the app can walk through history with undo/redo."""

    MAX_HISTORY_LENGTH: int = 200
    """Only this number of recent actions can be undone, to save memory."""

    liveState: FullState
    """State singleton that is being modified by the app."""

    undoStack: List[FullState]
    """List of previous state snapshots that can be undo'd to."""

    redoStack: List[FullState]
    """After undo, keep previous state in redo stack so undo can be redo'd."""

    def __init__(self, liveState: FullState) -> None:
        assert liveState is not None, "History must be created with non-None live state"
        self.liveState = liveState
        self.undoStack = []
        self.redoStack = []

    def pushState(self) -> FullState:
        """Remember the current live state so we can go back to it later if needed."""
        stateSnapshot = self._deepClone(self.liveState)
        self.undoStack.append(stateSnapshot)
        # Constrain size, make sure to not run out of memory:
        while len(self.undoStack) > History.MAX_HISTORY_LENGTH:
            del self.undoStack[0]

        self.redoStack = [] # Previous redo stack cleared on state push
        # print("History PUSH, #snapshots = (%d - %d)" % (len(self.undoStack), len(self.redoStack)))
        return stateSnapshot

    def undo(self) -> bool:
        """Revert live state back to the most recent pushed state."""
        if len(self.undoStack) == 0:
            return False # Cannot undo with nothing to undo back to.
        self.redoStack.append(self._deepClone(self.liveState))
        self._copyInto(self.undoStack.pop(), self.liveState)
        self._fixParents(self.liveState)
        # print("History UNDO, #snapshots = (%d - %d)" % (len(self.undoStack), len(self.redoStack)))
        return True

    def redo(self) -> bool:
        """Undo an undo by reverting the live stack to a recently undone state."""
        if len(self.redoStack) == 0:
            return False # Cannot redo with nothing to redo back insertPointBefore
        self.undoStack.append(self._deepClone(self.liveState))
        self._copyInto(self.redoStack.pop(), self.liveState)
        self._fixParents(self.liveState)
        # print("History REDO, #snapshots = (%d - %d)" % (len(self.undoStack), len(self.redoStack)))
        return True

    def _deepClone(self, modelToClone: FullState) -> FullState:
        """Perform a deep copy of the given object."""
        return copy.deepcopy(modelToClone)

    def _copyInto(self, modelFrom: FullState, modelTo: FullState) -> None:
        """Copy all field values from one object into another."""
        for field in attr.fields(modelFrom.__class__):
            setattr(modelTo, field.name, getattr(modelFrom, field.name))

    def _fixParents(self, liveState: FullState) -> None:
        """Cloning ruins parent references, this will put them back."""
        #if hasattr(liveState, 'uiStates'): # State is a fullState object
        for idx, uiState in enumerate(liveState.uiStates):
            uiState._parent = liveState
            uiState._tree = liveState.trees[idx]
        for tree in liveState.trees:
            self._fixTreeParents(tree)

        # TODO: Remove?
        #elif hasattr(liveState, 'branches'): # State is a tree
        #    self._fixTreeParents(liveState)

    def _fixTreeParents(self, tree: Tree) -> None:
        """Walk an entire tree and fix up branch and point parents."""
        for branch in tree.branches:
            branch._parentTree = tree
            for point in branch.points:
                point.parentBranch = branch
        for point in tree.flattenPoints():
            for child in point.children:
                child.parentPoint = point
