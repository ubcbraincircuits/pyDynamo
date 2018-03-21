import attr
import json
import gzip

from util import SAVE_KEY

from model import *

def attrFilter(attrData, value):
    return (SAVE_KEY in attrData.metadata) and attrData.metadata[SAVE_KEY]

def saveState(fullState, path):
    asDict = attr.asdict(fullState, filter=attrFilter)
    with gzip.GzipFile(path, 'w') as outfile:
        outfile.write(json.dumps(asDict, indent=2, sort_keys=True).encode('utf-8'))

### HACK - use cattrs?
def convert(asDict, key, conversion, isArray=False):
    if key not in asDict:
        return
    if not isArray:
        asDict[key] = conversion(asDict[key])
    else:
        asDict[key] = [conversion(value) for value in asDict[key]]


def convertToPoint(asDict):
    if asDict is None:
        return None
    convert(asDict, 'location', tuple)
    return Point(**asDict)

def convertToBranch(asDict):
    convert(asDict, 'parentPoint', convertToPoint)
    convert(asDict, 'points', convertToPoint, isArray=True)
    return Branch(**asDict)

def convertToTree(asDict):
    convert(asDict, 'rootPoint', convertToPoint)
    convert(asDict, 'branches', convertToBranch, isArray=True)
    return Tree(**asDict)

def convertToUIState(asDict):
    convert(asDict, 'colorLimits', tuple)
    return UIState(**asDict)

def convertToFullState(asDict):
    convert(asDict, 'trees', convertToTree, isArray=True)
    convert(asDict, 'uiStates', convertToUIState, isArray=True)
    return FullState(**asDict)

def indexTree(tree):
    for branch in tree.branches:
        branch._parentTree = tree
        for point in branch.points:
            point.parentBranch = branch
        # Replace local clone of point with proper reference
        if branch.parentPoint is not None: # Not sure what none signifies...
            properParent = tree.getPointByID(branch.parentPoint.id)
            if properParent is not None:
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
    fullState._nextPointID = findNextPointID(fullState)
    fullState._nextBranchID = findNextBranchID(fullState)
    fullState._rootPath = path
    return fullState

def loadState(path):
    asDict = None
    with gzip.GzipFile(path, 'r') as infile:
        asDict = json.loads(infile.read().decode('utf-8'))
    return indexFullState(convertToFullState(asDict), path)
