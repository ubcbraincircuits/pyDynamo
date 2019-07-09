import attr
import copy

import files

from model import *

def deepClone(obj):
    return copy.deepcopy(obj)

# Tests that a bunch of basic operations can be undone properly
def testTree():
    data = Tree()
    h = History(data)

    t0 = deepClone(data)
    assert data == t0

    pR = Point(id='root', location=(0,0,0))
    data.rootPoint = pR
    assert data != t0

    s0 = h.pushState()
    assert s0 == data
    assert s0 != t0

    b0 = Branch(id='b0')
    p1 = Point(id='p1', location=(0,0,1))
    b0.addPoint(p1)
    data.addBranch(b0)
    assert data != t0
    assert data != s0

    s1 = h.pushState()
    assert s1 == data
    assert s1 != s0

    p2 = Point(id='p2', location=(0,0,2))
    b0.addPoint(p2)
    t1 = deepClone(data)
    assert data != s1
    assert data == t1

    canUndo = h.undo()
    assert canUndo
    assert data != t1
    assert data == s1

    # Verify parent references are restored:
    for branch in data.branches:
        assert id(branch._parentTree) == id(data)
        for point in branch.points:
            assert id(point.parentBranch) == id(branch)
    for point in data.flattenPoints():
        for child in point.children:
            assert id(child.parentPoint) == id(point)

    canUndo = h.undo()
    assert canUndo
    assert data != t1
    assert data != s1
    assert data == s0

    # Verify parent references are restored:
    for branch in data.branches:
        assert id(branch._parentTree) == id(data)
        for point in branch.points:
            assert id(point.parentBranch) == id(branch)
    for point in data.flattenPoints():
        for child in point.children:
            assert id(child.parentPoint) == id(point)

    canUndo = h.undo()
    assert not canUndo

    canRedo = h.redo()
    assert canRedo
    assert data == s1
    print ("Tree history passed! 🙌")

# Tests that full states match for all the child UI states after undo
def testParents():
    fullState = files.loadState("pydynamo_brain/test/files/example2.dyn.gz")
    fullID = id(fullState)
    for uiState in fullState.uiStates:
        assert id(uiState.parent()) == fullID

    h = History(fullState)
    h.pushState()
    h.undo()

    for uiState in fullState.uiStates:
        assert id(uiState.parent()) == fullID
    print ("Full State history passed! 🙌")

# Tests that if you keep pushing state, you start dropping old ones.
def testMaxDepth():
    data = Tree()
    h = History(data)
    assert len(h.undoStack) == 0

    h.pushState()

    pR = Point(id='root', location=(0,0,0))
    data.rootPoint = pR
    assert len(h.undoStack) == 1

    for i in range(2 * History.MAX_HISTORY_LENGTH):
        h.pushState()

    numUndoes = 0
    while h.undo():
        # Returns False once undo stack is empty
        numUndoes += 1
    assert numUndoes == History.MAX_HISTORY_LENGTH
    assert h.liveState.rootPoint is not None
    print ("History length test passed! 🙌")


def run():
    testTree()
    testParents()
    testMaxDepth()
    return True

if __name__ == '__main__':
    run()
