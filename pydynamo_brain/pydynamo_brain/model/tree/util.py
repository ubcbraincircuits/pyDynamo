from __future__ import annotations

import numpy as np

from typing import List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    #from .branch import Branch
    from .point import Point
    from .tree import Tree

# Return all points one further along the tree than this
def findNextPoints(pointAt: Point) -> List[Point]:
    nextAlongBranch = pointAt.nextPointInBranch(1, noWrap=True)
    branchPoint = [] if nextAlongBranch is None else [nextAlongBranch]
    firstChildPoints = [b.points[0] for b in pointAt.children if len(b.points) > 0]
    return branchPoint + firstChildPoints

# Return all (A, B, C) adjacent triples
def findAllTriples(tree: Tree, pointAt: Point, pointBefore: Optional[Point]) -> List[Tuple[Point, Point, Point]]:
    nextPoints = findNextPoints(pointAt)
    triples = []
    for nextPoint in nextPoints:
        if pointBefore is not None:
            triples.append((pointBefore, pointAt, nextPoint))
        triples += findAllTriples(tree, nextPoint, pointAt)
    return triples

# Return all (A, B, C) adjacent triples where the angle AB->BC is sharp.
def findTightAngles(tree: Tree, ignoreZ: bool=True,
    sameBranchThresholdRad: float=(0.7*np.pi),
    newBranchThresholdRad: float=(0.85*np.pi)
) -> List[Tuple[Point, Point, Point, float]]:
    tightAngles: List[Tuple[Point, Point, Point, float]] = []

    if tree.rootPoint is None:
        return tightAngles

    allTriples = findAllTriples(tree, tree.rootPoint, None)

    for triple in allTriples:
        if triple[1].parentBranch is None or triple[2].parentBranch is None:
            continue

        sameBranch = (triple[1].parentBranch.id == triple[2].parentBranch.id)
        thresholdRad = sameBranchThresholdRad if sameBranch else newBranchThresholdRad

        xs, ys, zs = tree.worldCoordPoints(list(triple))
        if ignoreZ:
            zs = [0 for _ in zs]
        worldAt = [np.array([x, y, z]) for x, y, z in zip(xs, ys, zs)]
        AB, BC = worldAt[1] - worldAt[0], worldAt[2] - worldAt[1]

        cosAngle = np.dot(AB, BC) / (np.linalg.norm(AB) * np.linalg.norm(BC))
        angle = np.abs(np.arccos(cosAngle))
        if angle > thresholdRad:
            allWithAngle = (triple[0], triple[1], triple[2], np.degrees(angle))
            tightAngles.append(allWithAngle)

    return tightAngles
