from .baseOptions import BaseOptions

from ..functions import puncta

# Methods without custom options

class PunctaSizeOptions(BaseOptions):
    def __init__(self, name):
        super().__init__(name, puncta.perPunctaSize)

# Methods with custom options

class PunctaIntensityOptions(BaseOptions):
    def __init__(self, name):
        super().__init__(name, puncta.perPunctaIntensity)

    def fillOptions(self, frameLayout, currentState):
        super().fillOptions(frameLayout, currentState)

    def readOptions(self):
        localOptions = {}
        localOptions.update(super().readOptions())
        return localOptions

    def defaultValues(self):
        return {
            'channel': 0
        }
