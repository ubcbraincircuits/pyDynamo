from pydynamo_brain.model import Tree, Branch, Point
import pydynamo_brain.util as util

from typing import Any

# Calculate total dendritic branch length for a dendritic arbor.
def TDBL(tree: Tree,
    excludeAxon: bool=True,
    excludeBasal: bool=True,
    includeFilo: bool=True,
    filoDist: float=10.0,
    **kwargs: Any
) -> float:
    """Calculate TDBL for a given tree.

    Total Dendritic Branch Length (TDBL) is the sum of the lenths of all dendrites within the tree.

    Args:
        trees (list): The structure of the tree across time.
        excludeAxon (bool): Flag indicating whether axons should not contribute to TDBL.
        excludeBasal (bool): Flag indicating whether basal dendrites should not contribute to TDBL.
        includeFilo (bool): Flag indicating whether filo lengths should be included in TDBL.
        filoDist (float): Maximum distance a branch can be for it to be considered a filo.

    Returns:
        float: Sum of all dendritic length in the tree.
    """
    if not tree.rootPoint:
        return 0.0
    return _tdblPoint(tree.rootPoint, excludeAxon, excludeBasal, includeFilo, filoDist)

# TDBL for a single point, calculated as the TDBL of children off it.
def _tdblPoint(
    point: Point, excludeAxon: bool, excludeBasal: bool, includeFilo: bool, filoDist: float
) -> float:
    totalLength = 0.0
    for childBranch in point.children:
        totalLength += _tdblBranch(childBranch, excludeAxon, excludeBasal, includeFilo, filoDist)
    return totalLength

# TDBL of a branch, the TDBL for all children plus length along the branch.
# Optional filters can be applied to remove parts based on annotations.
def _tdblBranch(
    branch: Branch, excludeAxon: bool, excludeBasal: bool, includeFilo: bool, filoDist: float
) -> float:
    pointsWithRoot = branch.points
    if branch.parentPoint is not None:
        pointsWithRoot = [branch.parentPoint] + branch.points
    branchIdx = branch.indexInParent()

    # If the branch is 1) Empty, or 2) Axon and 3) Basal when desired, skip
    if branch.isEmpty() or (excludeAxon and branch.isAxon()) or (excludeBasal and branch.isBasal()):
        return 0.0

    # Add all the child branches...
    tdblLength = 0.0
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
