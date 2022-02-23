import math

from PyQt5.QtCore import QRect
from PyQt5.QtWidgets import QDesktopWidget

# pyqt5 version of matlab tilefigs function
def tileFigs(stackWindows):
    # Filter out only open windows:
    stackWindows = [w for w in stackWindows if w is not None]

    assert len(stackWindows) > 0
    hspc   = 10 # Horisontal space.
    topspc = 40 # Space above top figure.
    medspc = 40 # Space between figures.
    botspc = 10 # Space below bottom figure.

    # Get screen size
    geom = QDesktopWidget().availableGeometry()
    scrwid = geom.width()
    scrhgt = geom.height()

    # Set 'miscellaneous parameter' (??).
    ratio = (scrhgt * 0.5) / scrwid # ideal fraction of nv/nh (we will take ceil)
    nfigs = len(stackWindows) # Number of figures. i.e. nv*nh
    nv = max(1, math.ceil(math.sqrt(nfigs * ratio))) # Number of figures V.
    nh = max(2, math.ceil(nfigs / nv))		# Number of figures H.

    # Figure width and height
    figwid = (scrwid - (nh + 1) * hspc) / nh
    fighgt = (scrhgt - (topspc + botspc) - (nv - 1) * medspc) / nv

    # Put the figures where they belong
    for row in range(nv):
        for col in range(nh):
            idx = row * nh + col
            if idx < nfigs:
                figlft = (col + 1) * hspc + col * figwid
               	figtop = row * medspc + topspc + row * fighgt
                stackWindows[idx].resize(int(figwid), int(fighgt))
                stackWindows[idx].move(int(figlft), int(figtop))
                stackWindows[idx].redraw()
