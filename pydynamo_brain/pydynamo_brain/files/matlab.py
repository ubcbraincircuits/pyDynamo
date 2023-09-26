import numpy as np
import scipy.io as sio

from scipy.spatial.distance import euclidean

from pydynamo_brain.model import *
from pydynamo_brain.util import deltaSz

# Read a single branch from the matlab arrays containing per-point data
def parseMatlabBranch(fullState, pointsXYZ, annotations):
    branch = Branch(id=fullState.nextBranchID())
    for xyz, annotation in zip(pointsXYZ, annotations):
        assert xyz.shape == (3,)
        xyz = xyz - 1 # Matlab uses 1-based indices
        nextPoint = Point(
            id = fullState.nextPointID(),
            location = tuple(xyz * 1.0),
            annotation = ("" if len(annotation) == 0 else annotation[0])
        )
        branch.addPoint(nextPoint)
    return branch

# Read transform definition from the stack info
def parseTransform(infoState):
    t = Transform()
    if infoState.shape == (1,):
        infoState = infoState[0]
    t.rotation = infoState['R'][0][0].tolist()
    t.translation = infoState['offset'][0][0].T[0].tolist()
    t.scale = (infoState['xres'][0][0][0][0], infoState['yres'][0][0][0][0], infoState['zres'][0][0][0][0])
    return t

# Read a single tree, by reading in all its branches and hooking them up
def parseMatlabTree(fullState, saveState, removeOrphanBranches=True):
    tree = Tree()
    branchList = saveState['tree'][0]
    if branchList.shape == (1,):
        branchList = branchList[0]

    for i in range(branchList.shape[1]):
        # HACK: Matlab uses branch index as ID:
        fullState._nextBranchID = i

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
            branch.setParentPoint(rootPoint)
            branch.points[0].annotation = str(i)
            if i == 0: # First branch is special, as first node is tree root
                tree.rootPoint = rootPoint
                tree.rootPoint.parentBranch = None
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
                    if tree.branches[childIdx - 1].parentPoint is not None:
                        oldParent = tree.branches[childIdx - 1].parentPoint
                        newParent = tree.branches[i].points[j - 1]
                        moved = deltaSz(oldParent.location, newParent.location)
                        if moved > 0.01:
                            print("WARNING: Branch %d parent location has moved %f" % (childIdx - 1, moved))
                            print("%s to %s" % (
                                str(tree.branches[childIdx - 1].parentPoint.location),
                                str(tree.branches[i].points[j - 1].location)
                            ))
                            # HACK - add branch to children of parent, but keep old parent on branch
                            tree.branches[i].points[j - 1].children.append(tree.branches[childIdx - 1])
                            tree.branches[childIdx - 1].reparentTo = tree.branches[i].points[j - 1]
                            continue
                    tree.branches[childIdx - 1].setParentPoint(tree.branches[i].points[j - 1])

    if removeOrphanBranches:
        tree.branches = [b for b in tree.branches if b.parentPoint is not None]

    tree.transform = parseTransform(saveState['info'][0])
    return tree

def alignPointID(fullState):
    treeList = fullState.trees
    if len(treeList) <= 1:
        return fullState
    for i in range(len(treeList)-1):
        fullState.setPointIDWithoutCollision(treeList[i+1], treeList[i+1].rootPoint, treeList[i].rootPoint.id)

    for i in range(len(treeList)-1):
        treeShift = np.array(treeList[i+1].rootPoint.location) - np.array(treeList[i].rootPoint.location)
        
        
        _branchesT0 = [branch.id for branch in treeList[i].branches]
        _branchesT1 = [branch.id for branch in treeList[i+1].branches]
        for _branch in _branchesT0:
            if treeList[i+1].getBranchByID(_branch) is not None:
                if len(treeList[i+1].getBranchByID(_branch).points) == len(treeList[i].getBranchByID(_branch).points):
                    for pairPoints in zip(treeList[i+1].getBranchByID(_branch).points, treeList[i].getBranchByID(_branch).points): 
                        fullState.setPointIDWithoutCollision(treeList[i+1], pairPoints[0], pairPoints[1].id)    
                else:
                    _matchedPoint = None
                    for _pointT0 in treeList[i].getBranchByID(_branch).points:
                        for _pointT1 in treeList[i+1].getBranchByID(_branch).points:
                            #if treeList[i].getPointByID(_pointT1) is None:
                                #print(np.allclose(np.array(_pointT1.location), (np.array(_pointT0.location) + treeShift), atol=15))
                                #print(_pointT0.location, _pointT1.location)
                            if np.allclose(np.array(_pointT1.location), (np.array(_pointT0.location) + treeShift), atol=25):
                                if _matchedPoint is None:
                                    fullState.setPointIDWithoutCollision(treeList[i+1], _pointT1, _pointT0.id)
                                    _matchedPoint = _pointT0
                                else:
                                    if euclidean(np.array(_pointT1.location), (np.array(_pointT0.location) + treeShift)) <=  euclidean(np.array(_pointT1.location), (np.array(_matchedPoint.location) + treeShift)):
                                        fullState.setPointIDWithoutCollision(treeList[i+1], _pointT1, _pointT0.id)
                                        _matchedPoint = _pointT0    
        
        
        for _pointT1 in treeList[i+1].flattenPoints():
            if treeList[i].getPointByID(_pointT1.id) is None:
                _tempPoint = treeList[i].closestPointTo(np.array(_pointT1.location)-treeShift)
                if treeList[i+1].getPointByID(_tempPoint.id) is None:
                    print(np.array(_pointT1.location), (np.array(_tempPoint.location) + treeShift))
                    if _pointT1.parentBranch.id == _tempPoint.parentBranch.id:
                        fullState.setPointIDWithoutCollision(treeList[i+1], _pointT1, _tempPoint.id)

        for _pointT0 in treeList[i].flattenPoints():
            if treeList[i+1].getPointByID(_pointT0.id) is None:
                _tempPoint = treeList[i+1].closestPointTo(np.array(_pointT0.location)+treeShift)
                if treeList[i].getPointByID(_tempPoint.id) is None:
                    if _pointT0.parentBranch.id == _tempPoint.parentBranch.id:
                        print(np.array(_pointT1.location), (np.array(_tempPoint.location) + treeShift))
                        fullState.setPointIDWithoutCollision(treeList[i+1], _pointT1, _tempPoint.id)
                        
                            
                                    
    return fullState



# Load an existing dynamo matlab file, and convert it into the python dynamo format.
def importFromMatlab(matlabPath, removeOrphanBranches=True):
    fullState = FullState()
    filePaths, treeData = [], []

    mat = sio.loadmat(matlabPath)
    saveStates = None
    if 'saved' in mat.keys():
        # Original microscope code
        saveStates = mat['saved'][0]['Dynamo'][0]['state'][0][0]
    elif 'savedata' in mat.keys():
        # Just matlab dynamo code
        saveStates = mat['savedata'][0]['state'][0]
    else:
        raise Exception("Unrecognized matlab content")

    for i in range(saveStates.shape[1]):
        saveState = saveStates[0, i][0]
        filePath = saveState['info'][0]['filename'][0][0][0]
        filePaths.append(filePath)
        tree = parseMatlabTree(fullState, saveState, removeOrphanBranches)
        # Note: Pull out scale from transform, move it to global scale:
        fullState.projectOptions.pixelSizes = tree.transform.scale
        tree.transform.scale = (1, 1, 1)
        treeData.append(tree)
       
    fullState.addFiles(filePaths, treeData)
    fullState = alignPointID(fullState)
    return fullState
