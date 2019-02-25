from .baseOptions import BaseOptions

from ..functions import tree

# Methods without custom options

class PointCountOptions(BaseOptions):
    def __init__(self, name):
        super().__init__(name, tree.pointCount)

class BranchCountOptions(BaseOptions):
    def __init__(self, name):
        super().__init__(name, tree.branchCount)

# Methods with custom options

class TDBLOptions(BaseOptions):
    def __init__(self, name):
        super().__init__(name, tree.tdbl)

    def fillOptions(self, frameLayout, currentState):
        super().fillOptions(frameLayout, currentState)

    def readOptions(self):
        localOptions = {}
        localOptions.update(super().readOptions())
        return localOptions

    def defaultValues(self):
        return {
            'filoDist': 10,
            'includeFilo': True,
            'excludeAxon': True,
            'excludeBasal': True
        }
