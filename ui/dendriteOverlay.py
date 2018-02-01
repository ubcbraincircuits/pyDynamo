from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter
from PyQt5.QtWidgets import QWidget, QGridLayout, QApplication

from .dendritePainter import DendritePainter

class DendriteOverlay(QWidget):
    def __init__(self, dendriteCanvas, *args, **kwargs):
        super(QWidget, self).__init__(*args, **kwargs)
        self.dendriteCanvas = dendriteCanvas
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter()
        p.begin(self)
        DendritePainter(p,
            self.dendriteCanvas.uiState.parent().zAxisAt,
            self.dendriteCanvas.uiState,
            self.dendriteCanvas.imgView.mapFromScene
        ).drawTree(self.dendriteCanvas.model)
        p.end()
