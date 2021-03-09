from .baseOptions import BaseOptions

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.Qt import Qt

from typing import Any, Dict

import pydynamo_brain.util as util
from pydynamo_brain.model import FullState
from pydynamo_brain.analysis.functions import puncta

_IMG_CACHE = util.ImageCache()

# Methods without custom options

class PunctaSizeOptions(BaseOptions):
    def __init__(self, name: str) -> None:
        super().__init__(name, puncta.perPunctaSize)

# Methods with custom options

class PunctaIntensityOptions(BaseOptions):
    # One parameter supported: The channel used for puncta intensity.
    def __init__(self, name: str) -> None:
        super().__init__(name, puncta.perPunctaIntensity)

    def fillOptionsInner(self,
        currentState: Dict[str, Any], fullState: FullState, formParent: QtWidgets.QWidget
    ) -> None:
        self.channel = QtWidgets.QComboBox(formParent)

        nChannels = _IMG_CACHE.estimateChannelCount(fullState)
        for i in range(nChannels):
            self.channel.addItem("%d" % (i + 1))

        selected = currentState['channel'] if 'channel' in currentState else 0
        self.channel.setCurrentIndex(selected)

        self._addFormRow("Channel:", self.channel)

    def readOptions(self) -> Dict[str, Any]:
        localOptions = {
            'channel': self.channel.currentIndex()
        }
        localOptions.update(super().readOptions())
        return localOptions

    def defaultValues(self) -> Dict[str, Any]:
        return {
            'channel': 0
        }
