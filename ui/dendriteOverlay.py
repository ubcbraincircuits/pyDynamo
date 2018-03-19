from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter
from PyQt5.QtWidgets import QWidget, QGridLayout, QApplication

from .dendritePainter import DendritePainter
from .landmarkPainter import LandmarkPainter

class DendriteOverlay(QWidget):
    def __init__(self, dendriteCanvas, *args, **kwargs):
        super(QWidget, self).__init__(*args, **kwargs)
        self.dendriteCanvas = dendriteCanvas
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

    def paintEvent(self, event):
        super().paintEvent(event)
        fullState = self.dendriteCanvas.uiState.parent()

        p = QPainter()
        p.begin(self)

        if fullState.inLandmarkMode():
            LandmarkPainter(p,
                fullState.zAxisAt,
                self.dendriteCanvas.uiState,
                self.dendriteCanvas.imgView.mapFromScene
            ).drawLandmarks(self.dendriteCanvas.uiState._landmarks, fullState.landmarkPointAt)
        else:
            DendritePainter(p,
                fullState.zAxisAt,
                self.dendriteCanvas.uiState,
                self.dendriteCanvas.imgView.mapFromScene
            ).drawTree(self.dendriteCanvas.uiState._tree)
        p.end()
