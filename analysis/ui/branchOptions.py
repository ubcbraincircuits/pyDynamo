from .baseOptions import BaseOptions

from ..functions import branch

# Methods without custom options

class BranchLengthOptions(BaseOptions):
    def __init__(self, name):
        super().__init__(name, branch.branchLengths)

class IsAxonOptions(BaseOptions):
    def __init__(self, name):
        super().__init__(name, branch.branchHasAnnotationFunc('axon'))

class BranchParentIDOptions(BaseOptions):
    def __init__(self, name):
        super().__init__(name, branch.branchParentIDs)

# Methods with custom options

class BranchTypeOptions(BaseOptions):
    def __init__(self, name):
        super().__init__(name, branch.branchType)

    def fillOptions(self, frameLayout, currentState):
        super().fillOptions(frameLayout, currentState)

    def readOptions(self):
        localOptions = {}
        localOptions.update(super().readOptions())
        return localOptions

    def defaultValues(self):
        return {
            'filoDist': 10,
            'terminalDist': 10,
            'excludeAxon': True,
            'excludeBasal': True
        }
