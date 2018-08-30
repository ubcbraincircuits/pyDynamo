import os
import time
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import Qt, QPoint

from ui import DynamoWindow

import util
from util.testableFilePicker import setNextTestPaths

def _pointNear(locA, locB):
    return util.deltaSz(locA, locB) < 1e-9

def _init(qtbot):
    dynamoWindow = DynamoWindow(None, ["dynamo.py"])
    dynamoWindow.show()
    qtbot.addWidget(dynamoWindow)
    return dynamoWindow

def run(qtbot):
    dW = _init(qtbot)

    scan1Path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "files", "scan1.tif")

    # Click to open new stack:
    setNextTestPaths([scan1Path])
    qtbot.mouseClick(dW.initialMenu.buttonN, Qt.LeftButton)
    qtbot.waitUntil(lambda: len(dW.stackWindows) == 1)

    assert len(dW.fullState.trees) == 1
    tree = dW.fullState.trees[0]

    assert len(dW.fullState.filePaths) == 1
    assert len(dW.fullState.landmarks) == 1
    assert len(dW.fullState.uiStates) == 1
    assert tree.rootPoint is None
    assert len(tree.branches) == 0

    A = QPoint(100, 100)
    B = QPoint(100, 150)
    C = QPoint(150, 150)
    D = QPoint(150, 100)
    E = QPoint( 50, 150)
    sW = dW.stackWindows[0]
    view = sW.dendrites.imgView.viewport()

    STACK_OFFSET = 3

    # Draw first two sides of square
    qtbot.mouseClick(view, Qt.LeftButton, pos=A)
    assert tree.rootPoint is not None
    assert len(tree.flattenPoints()) == 1
    assert len(tree.branches) == 0

    qtbot.mouseClick(view, Qt.LeftButton, pos=B)
    assert len(tree.flattenPoints()) == 2
    assert len(tree.branches) == 1

    qtbot.mouseClick(view, Qt.LeftButton, pos=C)
    assert len(tree.flattenPoints()) == 3
    assert len(tree.branches) == 1

    # Move up three stacks, and draw the 4th point
    for i in range(STACK_OFFSET):
        qtbot.keyClick(sW, '1')

    qtbot.mouseClick(view, Qt.LeftButton, pos=D)
    assert len(tree.flattenPoints()) == 4
    assert len(tree.branches) == 1

    allZ = [p.location[2] for p in tree.flattenPoints()]
    assert allZ == [0, 0, 0, STACK_OFFSET]

    # Select the second point
    for i in range(STACK_OFFSET):
        qtbot.keyClick(sW, '2')
    qtbot.mouseClick(view, Qt.LeftButton, pos=B)

    points = tree.flattenPoints()
    assert len(points) == 4
    assert len(tree.branches) == 1
    assert dW.fullState.uiStates[0].currentPoint().id == points[1].id

    # Create a new child branch off it.
    qtbot.mouseClick(view, Qt.RightButton, pos=E)
    points = tree.flattenPoints()
    assert len(points) == 5
    assert len(tree.branches) == 2
    assert dW.fullState.uiStates[0].currentPoint().parentBranch.parentPoint.id == points[1].id

    # Reparent that from off B, to off C
    qtbot.keyClick(sW, 'r', Qt.ControlModifier)
    qtbot.mouseClick(view, Qt.LeftButton, pos=C)
    points = tree.flattenPoints()
    assert len(points) == 5
    assert len(tree.branches) == 2
    assert dW.fullState.uiStates[0].currentPoint().parentBranch.parentPoint.id == points[2].id
    
    return True
