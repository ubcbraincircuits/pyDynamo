import util

# Set this to a branch index to print TDBL information for that particular branch.
DEBUG_BRANCH = -1

# Calculate total dendritic branch length for a dendritic arbor.
def TDBL(tree,
    excludeAxon=True,
    excludeBasal=True,
    includeFilo=True,
    filoDist=10,
    debug=False
):
    if not tree.rootPoint:
        return 0
    return _tdblPoint(tree.rootPoint, excludeAxon, excludeBasal, includeFilo, filoDist, debug)

# TDBL for a single point, calculated as the TDBL of children off it.
def _tdblPoint(point, excludeAxon, excludeBasal, includeFilo, filoDist, debug):
    totalLength = 0
    for childBranch in point.children:
        totalLength += _tdblBranch(childBranch, excludeAxon, excludeBasal, includeFilo, filoDist, debug)
    return totalLength

# TDBL of a branch, the TDBL for all children plus length along the branch.
# Optional filters can be applied to remove parts based on annotations.
def _tdblBranch(branch, excludeAxon, excludeBasal, includeFilo, filoDist, DEBUG):
    pointsWithRoot = [branch.parentPoint] + branch.points
    branchIdx = branch.indexInParent()

    # 1) If the branch has not been created yet, or is empty, abort
    if len(pointsWithRoot) < 2:
        return 0
    # 2) If the branch contains an 'axon' label, abort
    if excludeAxon and _lastPointWithLabel(pointsWithRoot, 'axon') >= 0:
        return 0
    # 3) If the branch is a basal dendrite, abort
    if excludeBasal and _lastPointWithLabel(pointsWithRoot, 'basal') >= 0:
        return 0

    # Add all the child branches...
    tdblLength = 0
    for point in branch.points:
        tdblLength += _tdblPoint(point, excludeAxon, excludeBasal, includeFilo, filoDist, DEBUG)
    if DEBUG:
        print ("TDBL for branch %d after children = %.3f" % (branchIdx + 1, tdblLength))

    # ... then remove any points up to and including the last point marked 'soma'
    somaIdx = _lastPointWithLabel(pointsWithRoot, 'soma')
    if somaIdx >= 0:
        pointsWithRoot = pointsWithRoot[somaIdx+1:]

    # ... measure distance for entire branch, and up to last branchpoint:
    totalLength, totalLengthToLastBranch = branch.worldLengths()
    if DEBUG and branchIdx == DEBUG_BRANCH:
        print ([p.location for p in [branch.parentPoint] + branch.points])
        print('%d has dist/branchdist %.4f/%.4f' % (branchIdx, totalLength, totalLengthToLastBranch))

    # Use full distance only if including filo, or if the end isn't a filo.
    if includeFilo or (totalLength - totalLengthToLastBranch) > filoDist:
        tdblLength += totalLength
    else:
        tdblLength += totalLengthToLastBranch
    if DEBUG:
        print ("TDBL for branch %d = %.3f" % (branch.indexInParent() + 1, tdblLength))
    return tdblLength

# Return the index of the last point whose label contains given text, or -1 if not found.
# TODO - move somewhere common.
def _lastPointWithLabel(points, label):
    lastPointIdx = -1
    for i, point in enumerate(points):
        if point.annotation.find(label) != -1:
            lastPointIdx = i
    return lastPointIdx
