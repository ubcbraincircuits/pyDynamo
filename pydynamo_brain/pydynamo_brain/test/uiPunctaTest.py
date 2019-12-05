import os
import time
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import Qt, QPoint

from pydynamo_brain.ui import DynamoWindow

import pydynamo_brain.util as util
from pydynamo_brain.util.testableFilePicker import setNextTestPaths

from pydynamo_brain.files import fullStateToString, stringToFullState

def _near(a, b):
    return abs(a - b) < 1e-6

def _checkPointXYZR(p, x, y, z, r):
    assert _near(x, p.location[0]) \
        and _near(y, p.location[1]) \
        and _near(z, p.location[2]) \
        and _near(r, p.radius)

def _init(qtbot):
    dynamoWindow = DynamoWindow(None, [])
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
    sW = dW.stackWindows[0]
    view = sW.dendrites.imgView.viewport()

    # Wait til window is ready:
    qtbot.mouseClick(view, Qt.LeftButton, pos=QPoint(0, 0))
    sW.raise_()
    sW.activateWindow()
    sW.setFocus(True)
    qtbot.waitUntil(lambda: sW.hasFocus(), timeout=10000)

    # Empty tree, no puncta
    assert len(dW.fullState.trees) == 1
    assert len(dW.fullState.puncta) == 0

    # Enter puncta mode
    qtbot.keyClick(sW, 'p')
    assert dW.fullState.inPunctaMode()

    pDraw = QPoint(100, 100)
    pMove = QPoint(100, 150)
    pSize = QPoint(103, 154)

    x1 = 55.2423679
    y1 = 44.1938943
    r1 = 3.0000000
    y2 = 71.8150782
    r2 = 2.7621184


    # Draw the point
    qtbot.mouseClick(view, Qt.LeftButton, pos=pDraw)
    assert len(dW.fullState.puncta) == 1
    assert len(dW.fullState.puncta[0]) == 1
    point = dW.fullState.puncta[0][0]
    _checkPointXYZR(point, x1, y1, 0, r1)

    # Move the point
    qtbot.mouseClick(view, Qt.LeftButton, pos=pMove, modifier=Qt.ShiftModifier)
    assert len(dW.fullState.puncta) == 1
    assert len(dW.fullState.puncta[0]) == 1
    point = dW.fullState.puncta[0][0]
    _checkPointXYZR(point, x1, y2, 0, r1)

    # Resize the point
    qtbot.mouseClick(view, Qt.RightButton, pos=pSize)
    assert len(dW.fullState.puncta) == 1
    assert len(dW.fullState.puncta[0]) == 1
    point = dW.fullState.puncta[0][0]
    _checkPointXYZR(point, x1, y2, 0, r2)

    # Draw a second point:
    qtbot.mouseClick(view, Qt.LeftButton, pos=pDraw)
    assert len(dW.fullState.puncta) == 1
    assert len(dW.fullState.puncta[0]) == 2
    point = dW.fullState.puncta[0][1]
    _checkPointXYZR(point, x1, y1, 0, r1)

    # Delete the first point by clicking on its boundary:
    qtbot.mouseClick(view, Qt.LeftButton, pos=pSize, modifier=Qt.ControlModifier)
    assert len(dW.fullState.puncta) == 1
    assert len(dW.fullState.puncta[0]) == 1
    # ... only the second point left
    point = dW.fullState.puncta[0][0]
    _checkPointXYZR(point, x1, y1, 0, r1)

    # Save and load to verify
    toString = fullStateToString(dW.fullState)
    toFullState = stringToFullState(toString, "")
    assert len(toFullState.puncta) == 1
    assert len(toFullState.puncta[0]) == 1
    point = toFullState.puncta[0][0]
    _checkPointXYZR(point, x1, y1, 0, r1)

    return True
