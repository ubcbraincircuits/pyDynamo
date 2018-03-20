import util

# Calculate total dendritic branch length for a dendritic arbor.
def TDBL(tree,
    excludeAxon=True,
    excludeBasal=True,
    includeFilo=True,
    filoDist=10
):
    """TODO - document."""
    if not tree.rootPoint:
        return 0
    return _tdblPoint(tree.rootPoint, excludeAxon, excludeBasal, includeFilo, filoDist)

# TDBL for a single point, calculated as the TDBL of children off it.
def _tdblPoint(point, excludeAxon, excludeBasal, includeFilo, filoDist):
    totalLength = 0
    for childBranch in point.children:
        totalLength += _tdblBranch(childBranch, excludeAxon, excludeBasal, includeFilo, filoDist)
    return totalLength

# TDBL of a branch, the TDBL for all children plus length along the branch.
# Optional filters can be applied to remove parts based on annotations.
def _tdblBranch(branch, excludeAxon, excludeBasal, includeFilo, filoDist):
    pointsWithRoot = [branch.parentPoint] + branch.points
    branchIdx = branch.indexInParent()

    # If the branch is 1) Empty, or 2) Axon and 3) Basal when desired, skip
    if branch.isEmpty() or (excludeAxon and branch.isAxon()) or (excludeBasal and branch.isBasal()):
        return 0

    # Add all the child branches...
    tdblLength = 0
    for point in branch.points:
        tdblLength += _tdblPoint(point, excludeAxon, excludeBasal, includeFilo, filoDist)

    # ... then remove any points up to and including the last point marked 'soma'
    somaIdx = util.lastPointWithLabelIdx(pointsWithRoot, 'soma')

    # ... measure distance for entire branch, and up to last branchpoint:
    totalLength, totalLengthToLastBranch = branch.worldLengths(fromIdx=(somaIdx+1))

    # Use full distance only if including filo, or if the end isn't a filo.
    if includeFilo or (totalLength - totalLengthToLastBranch) > filoDist:
        tdblLength += totalLength
    else:
        tdblLength += totalLengthToLastBranch
    return tdblLength
