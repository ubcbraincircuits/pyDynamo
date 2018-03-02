import numpy as np
import scipy.io as sio

from model import *

# Read a single branch from the matlab arrays containing per-point data
def parseMatlabBranch(fullState, pointsXYZ, annotations):
    branch = Branch(id=fullState.nextBranchID())
    for xyz, annotation in zip(pointsXYZ, annotations):
        assert xyz.shape == (3,)
        branch.addPoint(Point(
            id = fullState.nextPointID(),
            location = tuple(xyz),
            annotation = ("" if len(annotation) == 0 else annotation[0])
        ))
    return branch

# Read a single tree, by reading in all its branches and hooking them up
def parseMatlabTree(fullState, saveState):
    tree = Tree()
    branchList = saveState['tree'][0]

    for i in range(branchList.shape[1]):
        if len(branchList[0, i]) > 0:
            # Load in branch:
            branchData = branchList[0, i][0]
            branch = parseMatlabBranch(fullState,
                branchData[0].T,  # XYZ position
                branchData[2][0], # Annotations
            )

            # ... and remove first point as it is duplicated data from parent:
            rootPoint = branch.points[0]
            branch.removePointLocally(rootPoint)
            if i == 0: # First branch is special, as first node is tree root
                branch.parentPoint = rootPoint
                tree.rootPoint = rootPoint
        else:
            # No branch data? Not sure what caused this in matlab...
            branch = Branch(fullState.nextBranchID())
        tree.addBranch(branch)

    # For each point, hook up its child branches to it:
    for i in range(branchList.shape[1]):
        if len(branchList[0, i]) > 0:
            childListForPoints = branchList[0, i][0][1][0] # Child index list
            for j, childListForPoint in enumerate(childListForPoints):
                for childIdx in np.nditer(childListForPoint, ['refs_ok', 'zerosize_ok']):
                    tree.branches[childIdx - 1].parentPoint = tree.branches[i].points[j - 1]
    return tree

# Load an existing dynamo matlab file, and convert it into the python dynamo format.
def importFromMatlab(matlabPath):
    fullState = FullState()
    filePaths, treeData = [], []

    mat = sio.loadmat(matlabPath)
    saveStates = mat['savedata'][0]['state'][0]
    for i in range(saveStates.shape[1]):
        saveState = saveStates[0, i][0]
        filePath = saveState['info'][0]['filename'][0][0][0]
        # TODO: check whether file exists, and prompt if not...
        filePaths.append(filePath)
        treeData.append(parseMatlabTree(fullState, saveState))
    fullState.addFiles(filePaths, treeData)
    return fullState
