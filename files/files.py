import attr
import json
import gzip
import numpy as np

from util import SAVE_KEY

from model import *

def attrFilter(attrData, value):
    return (SAVE_KEY in attrData.metadata) and attrData.metadata[SAVE_KEY]

# https://stackoverflow.com/questions/11942364/typeerror-integer-is-not-json-serializable-when-serializing-json-in-python
def npInt64Fix(o):
    if isinstance(o, np.int64):
        print ("WARNING: Wrong data type (i64) for ", o, " - converting to int")
        return int(o)
    if type(o) is np.ndarray:
        print ("WARNING: Wrong data type (numpy array) for ", o, " - converting to list")
        return o.tolist()
    print ("ERROR - Can't save type: ", type(o))
    raise TypeError

def fullStateToString(fullState, filter=attrFilter):
    asDict = attr.asdict(fullState, filter=filter)
    return json.dumps(asDict, indent=2, sort_keys=True, default=npInt64Fix).encode('utf-8')

def saveState(fullState, path):
    with gzip.GzipFile(path, 'w') as outfile:
        outfile.write(fullStateToString(fullState))

### HACK - use cattrs?
def convert(asDict, key, conversion, isArray=False):
    if key not in asDict:
        return
    if not isArray:
        asDict[key] = conversion(asDict[key])
    else:
        asDict[key] = [conversion(value) for value in asDict[key]]

def convertToListOfTuples(asDict):
    return [tuple(value) for value in asDict]

def convertToPoint(asDict):
    if asDict is None:
        return None
    convert(asDict, 'location', tuple)
    return Point(**asDict)

def convertToTransform(asDict):
    return Transform(**asDict)

def convertToBranch(asDict):
    convert(asDict, 'parentPoint', convertToPoint)
    convert(asDict, 'reparentTo', convertToPoint)
    convert(asDict, 'points', convertToPoint, isArray=True)
    return Branch(**asDict)

def convertToTree(asDict):
    convert(asDict, 'rootPoint', convertToPoint)
    convert(asDict, 'branches', convertToBranch, isArray=True)
    convert(asDict, 'transform', convertToTransform)
    return Tree(**asDict)

def convertToUIState(asDict):
    convert(asDict, 'colorLimits', tuple)
    return UIState(**asDict)

def convertToMotilityOptions(asDict):
    return MotilityOptions(**asDict)

def convertToProjectOptions(asDict):
    convert(asDict, 'motilityOptions', convertToMotilityOptions)
    return ProjectOptions(**asDict)

def convertToFullState(asDict):
    convert(asDict, 'trees', convertToTree, isArray=True)
    convert(asDict, 'uiStates', convertToUIState, isArray=True)
    convert(asDict, 'landmarks', convertToListOfTuples, isArray=True)
    convert(asDict, 'projectOptions', convertToProjectOptions)
    return FullState(**asDict)

def indexTree(tree):
    for branch in tree.branches:
        branch._parentTree = tree
        for point in branch.points:
            point.parentBranch = branch

        # Deal with the case where the branch had the wrong parent in matlab.
        parent = branch.reparentTo or branch.parentPoint

        # Replace local clone of point with proper reference
        if parent is not None: # Not sure what none signifies...
            properParent = tree.getPointByID(parent.id, includeDisconnected=True)
            if properParent is not None:
                if branch.reparentTo is not None:
                    branch.reparentTo = properParent
                    properParent.children.append(branch)
                else:
                    branch.setParentPoint(properParent)

def findNextPointID(fullState):
    nextID = 0
    for tree in fullState.trees:
        for point in tree.flattenPoints():
            nextID = max(nextID, 1 + int(point.id, 16))
    return nextID

def findNextBranchID(fullState):
    nextID = 0
    for tree in fullState.trees:
        for branch in tree.branches:
            nextID = max(nextID, 1 + int(branch.id, 16))
    return nextID

def indexFullState(fullState, path):
    for tree in fullState.trees:
        indexTree(tree)
    for i, state in enumerate(fullState.uiStates):
        state._parent = fullState
        state._tree = fullState.trees[i]
        state._tree._parentState = state
        state.imagePath = fullState.filePaths[i]
    fullState._nextPointID = findNextPointID(fullState)
    fullState._nextBranchID = findNextBranchID(fullState)
    fullState._rootPath = path
    return fullState

def loadState(path):
    asDict = None
    with gzip.GzipFile(path, 'r') as infile:
        asDict = json.loads(infile.read().decode('utf-8'))
    return indexFullState(convertToFullState(asDict), path)

def checkIfChanged(fullState, path):
    if path is None:
        return True
    oldString = fullStateToString(loadState(path))
    newString = fullStateToString(fullState)
    return oldString != newString
