from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter
from PyQt5.QtWidgets import QWidget, QGridLayout, QApplication

import numpy as np

from .dendritePainter import DendritePainter
from .landmarkPainter import LandmarkPainter
from .punctaPainter import PunctaPainter

class DendriteOverlay(QWidget):
    def __init__(self, dendriteCanvas, windowIndex, *args, **kwargs):
        super(QWidget, self).__init__(*args, **kwargs)
        self.dendriteCanvas = dendriteCanvas
        self.windowIndex = windowIndex
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

    def updateWindowIndex(self, newIndex):
        self.windowIndex = newIndex

    def paintEvent(self, event):
        super().paintEvent(event)
        fullState = self.dendriteCanvas.uiState.parent()

        p = QPainter()
        p.begin(self)

        if fullState.inPunctaMode:
            puncta = []
            if (self.windowIndex < len(fullState.puncta)):
                puncta = fullState.puncta[self.windowIndex]
            PunctaPainter(p,
                self.windowIndex,
                self.dendriteCanvas.uiState,
                self.dendriteCanvas.imgView.mapFromScene,
                self.dendriteCanvas.imgView.fromSceneDist
            ).drawPuncta(puncta)
        elif fullState.inLandmarkMode():
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
                self.dendriteCanvas.imgView.mapFromScene,
                self.dendriteCanvas.imgView.fromSceneDist
            ).drawTree(self.dendriteCanvas.uiState._tree)
        p.end()
