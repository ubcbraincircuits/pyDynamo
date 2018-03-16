import attr
import copy

from model import *

def deepClone(obj):
    return copy.deepcopy(obj)

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

    canUndo = h.undo()
    assert canUndo
    assert data != t1
    assert data != s1
    assert data == s0

    canUndo = h.undo()
    assert not canUndo

    canRedo = h.redo()
    assert canRedo
    assert data == s1
    print ("History test passed! 🙌")


if __name__ == '__main__':
    testTree()
