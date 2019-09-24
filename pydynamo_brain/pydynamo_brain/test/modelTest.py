from pydynamo_brain.model import *

def testBranchOrder():
    """
    pR
    |
    p1
    |  \
    p2   p5 -- p6
    |  \    \
    p3  p4    p7

    b0: pR-p1-p2-p3
    b1: p2-p4
    b2: p1-p5-p7
    b3: p5-p6
    """
    tree = Tree()
    pR = Point(id='root', location=(0,0,0))
    tree.rootPoint = pR

    p1 = Point(id='p1', location=(0,0,1))
    p2 = Point(id='p2', location=(0,0,2))
    p3 = Point(id='p3', location=(0,0,3))
    p4 = Point(id='p4', location=(0,1,1))
    p5 = Point(id='p5', location=(0,1,2))
    p6 = Point(id='p6', location=(0,2,2))
    p7 = Point(id='p7', location=(0,3,3))

    b0 = Branch(id='b0')
    b1 = Branch(id='b1')
    b2 = Branch(id='b2')
    b3 = Branch(id='b3')

    b0.setParentPoint(pR)
    b0.addPoint(p1)
    b0.addPoint(p2)
    b0.addPoint(p3)
    b1.setParentPoint(p2)
    b1.addPoint(p4)
    b2.setParentPoint(p1)
    b2.addPoint(p5)
    b2.addPoint(p7)
    b3.setParentPoint(p5)
    b3.addPoint(p6)

    branches = [b0, b1, b2, b3]
    for b in branches:
        tree.addBranch(b)

    shaftOrders = [b.getOrder() for b in branches]
    centrifugalOrders = [b.getOrder(centrifugal=True) for b in branches]

    assert shaftOrders[0] == 1
    assert shaftOrders[1] == 2
    assert shaftOrders[2] == 2
    assert shaftOrders[3] == 3

    assert centrifugalOrders[0] == 1
    assert centrifugalOrders[1] == 3 # comes off root branch after other children
    assert centrifugalOrders[2] == 2
    assert centrifugalOrders[3] == 3

def run():
    testBranchOrder()
    return True

if __name__ == '__main__':
    run()
