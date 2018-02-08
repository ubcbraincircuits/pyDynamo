import attr
import json

from util import SAVE_KEY

from model import Point, Branch, Tree, UIState, FullState

def attrFilter(attrData, value):
    return (SAVE_KEY in attrData.metadata) and attrData.metadata[SAVE_KEY]

def saveState(fullState, path):
    asDict = attr.asdict(fullState, filter=attrFilter)
    with open(path, 'w') as outfile:
        json.dump(asDict, outfile, indent=2, sort_keys=True)


### HACK - use cattrs?
def convert(asDict, key, conversion, isArray=False):
    if key not in asDict:
        return
    if not isArray:
        asDict[key] = conversion(asDict[key])
    else:
        asDict[key] = [conversion(value) for value in asDict[key]]


def convertToPoint(asDict):
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
            # point.children = [] # HACK - implement or remove children property...

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
    with open(path, 'r') as infile:
        asDict = json.load(infile)
    return indexFullState(convertToFullState(asDict), path)
