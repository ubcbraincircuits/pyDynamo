import numpy as np

# Return all points one further along the tree than this
def findNextPoints(pointAt):
    nextAlongBranch = pointAt.nextPointInBranch(1, noWrap=True)
    branchPoint = [] if nextAlongBranch is None else [nextAlongBranch]
    firstChildPoints = [b.points[0] for b in pointAt.children]
    return branchPoint + firstChildPoints

# Return all (A, B, C) adjacent triples
def findAllTriples(tree, pointAt, pointBefore):
    nextPoints = findNextPoints(pointAt)
    triples = []
    for nextPoint in nextPoints:
        if pointBefore is not None:
            triples.append((pointBefore, pointAt, nextPoint))
        triples += findAllTriples(tree, nextPoint, pointAt)
    return triples

# Return all (A, B, C) adjacent triples where the angle AB->BC is sharp.
def findTightAngles(tree, ignoreZ=True,
    sameBranchThresholdRad=(0.7*np.pi), newBranchThresholdRad=(0.85*np.pi)
):
    tightAngles = []
    allTriples = findAllTriples(tree, tree.rootPoint, None)

    for triple in allTriples:
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
            tightAngles.append(tuple(list(triple) + [np.degrees(angle)]))

    return tightAngles
