from collections import deque
import os

from pydynamo_brain.model import *

###
### IMPORT
###

# SWC file -> Tree
def importFromSWC(path):
    childMap, metadata, comments = {}, {}, []

    swcLines = [line.rstrip('\n') for line in open(path)]
    for line in swcLines:
        # Process metdata values into map:
        metaKey, metaValue = _parseMeta(line)
        if metaKey is not None:
            metadata[metaKey] = metaValue

        # Collect comments, just in case it's useful for later:
        if line[0] == '#':
            comments.append(line)
            continue

        # And otherwise, build the tree:
        # n,type,x,y,z,radius,parent
        parts = line.split(' ')
        if len(parts) != 7:
            print ("Unsupported SWC file format. All node lines must be n,type,x,y,z,radius,parent")
            return None
        nodeID, nodeType, x, y, z, radius, parent = tuple(parts)
        x, y, z, radius = float(x), float(y), float(z), float(radius) # TODO: Scale?
        if parent not in childMap:
            childMap[parent] = []
        childMap[parent].append((nodeID, (x, y, z), radius)) # TODO: Use nodeType later?

    return _convertChildMapToTree(childMap)

# Given mapping of parent -> list of (child ID, child XYZ), convert this to a tree model
def _convertChildMapToTree(childMap):
    if '-1' not in childMap or len(childMap['-1']) != 1:
        print ("Can't parse SWC file: Has more than one Soma (parent -1)")
        return None
    somaID, somaLocation, somaRadius = childMap['-1'][0]

    tree = Tree()
    tree.rootPoint = Point(somaID, somaLocation, somaRadius)

    # Keep track of where branches have come off that still need processing
    toProcess = deque()
    toProcess.append(somaID)

    branchCounter = 0
    while len(toProcess) > 0:
        nextParentID = toProcess.popleft()
        nLeft = sum([len(childMap[k]) for k in childMap])
        print ("%d remain, Processing %s " % (nLeft, nextParentID))
        if nextParentID not in childMap or len(childMap[nextParentID]) == 0:
            continue
        parentPoint = tree.getPointByID(nextParentID)
        assert parentPoint is not None

        # Start this branch, but remember parent if it has more coming off...
        branchPointID, branchPointLocation, branchPointRadius = childMap[nextParentID][0]
        childMap[nextParentID].pop(0)
        if len(childMap[nextParentID]) > 0:
            toProcess.append(nextParentID)

        newBranch = Branch('%04x' % branchCounter)
        newBranch.setParentPoint(parentPoint)
        branchCounter += 1

        while True:
            # Walk along the branch, adding points as we go
            newBranch.addPoint(Point(branchPointID, branchPointLocation, branchPointRadius))
            oldBranchPointID = branchPointID
            if branchPointID not in childMap or len(childMap[branchPointID]) == 0:
                break
            # Remember any intermediate points that have more children coming off them
            branchPointID, branchPointLocation, branchPointRadius = childMap[oldBranchPointID][0]
            childMap[oldBranchPointID].pop(0)
            if len(childMap[oldBranchPointID]) > 0:
                toProcess.append(oldBranchPointID)
        tree.addBranch(newBranch)
    # Done!
    return tree


# Parse initial lines, like #SR_ratio = 0.333333
def _parseMeta(line):
    if line[0] != '#' or '=' not in line:
        return None, None
    at = line.find('=')
    return line[1:at].strip(), line[at+1:].strip()

###
### EXPORT
###

# Write tree back out to SWC
def exportToSWC(dirPath, filePath, tree, fullState, forNeuroM=False):
    totalPath = os.path.join(dirPath, filePath)
    with open(totalPath, 'w') as file:
        _exportHeader(file, tree, filePath, fullState)
        _exportNodes(file, tree, forNeuroM)

# Writes the SWC header, a bunch of key=value pairs in SWC comments
def _exportHeader(file, tree, filePath, fullState):
    (_, zSz, xSz, ySz) = fullState.volumeSize
    file.write("#name %s\n" % filePath)
    file.write("#comment\n")
    file.write("##Generated by pyDynamo\n")
    file.write("#channel = %d\n" % fullState.channel) #HACK
    # Overall dimensions
    file.write("#xc0 = 0\n#xc1 = %d\n" % xSz)
    file.write("#yc0 = 0\n#yc1 = %d\n" % ySz)
    file.write("#zc0 = 0\n#zc1 = %d\n" % zSz)

# Writes out each point's data in the standard format.
def _exportNodes(file, tree, forNeuroM=False):
    allPoints = tree.flattenPoints()

    # Maps node IDs (strings of base-16 numbers) to SWC indexes (1-based ints)
    idToSWCIndex = {}
    indexAt = 1
    for point in allPoints:
        if point.id not in idToSWCIndex:
            idToSWCIndex[point.id] = indexAt
            indexAt += 1

    file.write("##n,type,x,y,z,radius,parent\n")
    for point in tree.flattenPoints():
        n = idToSWCIndex[point.id]
        if forNeuroM:
            #      0        1     2         3                4              5          6         7
            # (UNDEFINED, SOMA, AXON, BASAL_DENDRITE, APICAL_DENDRITE, FORK_POINT, END_POINT, CUSTOM)
            type = 0
            if point.isRoot():
                type = 1 # Soma
            else:
                type = 3 # Force everything else to be BASAL for now...

            x, y, z = tree.worldCoordPoints([point])
            x, y, z = x[0], y[0], z[0]
            radius = point.radius if point.radius is not None else 1
            radius = tree.worldCoordPoints([(radius, radius, radius)])[0][0]

        else: # For Vaa 3D
            # Note: Vaa3D appears to encode branch ID in this property?
            type = int(point.parentBranch.id, 16) if point.parentBranch is not None else -1
            x, y, z = point.location
            radius = point.radius if point.radius is not None else 1
        nextPoint = point.nextPointInBranch(delta=-1)
        parent = -1 if nextPoint is None else idToSWCIndex[nextPoint.id]
        file.write("%d %d %.4f %.4f %.4f %.5f %d\n" % (n,type,x,y,z,radius,parent))
