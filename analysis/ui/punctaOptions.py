from .baseOptions import BaseOptions

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.Qt import Qt

from ..functions import puncta

# Methods without custom options

class PunctaSizeOptions(BaseOptions):
    def __init__(self, name):
        super().__init__(name, puncta.perPunctaSize)

# Methods with custom options

class PunctaIntensityOptions(BaseOptions):
    # One parameter supported: The channel used for puncta intensity.
    def __init__(self, name):
        super().__init__(name, puncta.perPunctaIntensity)

    def fillOptionsInner(self, currentState, formParent):
        self.channel = QtWidgets.QComboBox(formParent)

        nChannels = 2 # TODO
        for i in range(nChannels):
            self.channel.addItem("%d" % (i + 1))

        selected = currentState['channel'] if 'channel' in currentState else 0
        self.channel.setCurrentIndex(selected)

        self._addFormRow("Channel:", self.channel)

    def readOptions(self):
        localOptions = {
            'channel': self.channel.currentIndex()
        }
        localOptions.update(super().readOptions())
        return localOptions

    def defaultValues(self):
        return {
            'channel': 0
        }
