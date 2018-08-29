from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter
from PyQt5.QtWidgets import QWidget, QGridLayout, QApplication

from .dendritePainter import DendritePainter
from .landmarkPainter import LandmarkPainter

class DendriteOverlay(QWidget):
    def __init__(self, dendriteCanvas, windowIndex, *args, **kwargs):
        super(QWidget, self).__init__(*args, **kwargs)
        self.dendriteCanvas = dendriteCanvas
        self.windowIndex = windowIndex
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

    def paintEvent(self, event):
        super().paintEvent(event)
        fullState = self.dendriteCanvas.uiState.parent()

        p = QPainter()
        p.begin(self)

        if fullState.inLandmarkMode():
            landmarks = []
            if (self.windowIndex < len(fullState.landmarks)):
                landmarks = fullState.landmarks[self.windowIndex]
            LandmarkPainter(p,
                self.dendriteCanvas.uiState,
                self.dendriteCanvas.imgView.mapFromScene
            ).drawLandmarks(landmarks, fullState.landmarkPointAt)
        else:
            DendritePainter(p,
                self.dendriteCanvas.uiState,
                self.dendriteCanvas.imgView.mapFromScene
            ).drawTree(self.dendriteCanvas.uiState._tree)
        p.end()
