import numpy as np

from pydynamo_brain.util import listWithoutIdx

class IdAligner():
    treeA = None
    treeB = None

    maxSkip = 3
    updateFunc = None
    unmatchedPenalty = 10

    # Memoized results
    resultCache = {}

    # Per-point property caches
    nextPointsCache = {}
    subtreeSizeCache = {}

    def __init__(self, treeA, treeB, maxSkip=3, unmatchedPenalty=10):
        self.treeA = treeA
        self.treeB = treeB
        self.maxSkip = maxSkip
        self.unmatchedPenalty = unmatchedPenalty
        self.resultCache = {}
        self.nextPointsCache = {}
        self.subtreeSizeCache = {}

        self.subtreeCount('A', self.treeA.rootPoint)
        self.subtreeCount('B', self.treeB.rootPoint)

    # Given a point, find all points one step down the tree:
    def nextPoints(self, treeID, point):
        key = '%s:%s' % (treeID, point.id)
        if key not in self.nextPointsCache:
            nextAlongBranch = point.nextPointInBranch(1, noWrap=True)
            branchPoint = [] if nextAlongBranch is None else [nextAlongBranch]
            firstChildPoints = [b.points[0] for b in point.children]
            self.nextPointsCache[key] = branchPoint + firstChildPoints
        return self.nextPointsCache[key]

    # Calculates the number of points in the subtree rooted at the given point.
    def subtreeCount(self, treeID, point):
        key = '%s:%s' % (treeID, point.id)
        if key not in self.subtreeSizeCache:
            pointCount = 1
            for nextPoint in self.nextPoints(treeID, point):
                pointCount += self.subtreeCount(treeID, nextPoint)
            self.subtreeSizeCache[key] = pointCount
        return self.subtreeSizeCache[key]

    # Calculutes the max number of entries the cache can have.
    def maxCallCount(self):
        nA = self.subtreeCount('A', self.treeA.rootPoint)
        nB = self.subtreeCount('B', self.treeB.rootPoint)
        return nA * nB * self.maxSkip * self.maxSkip

    # Find all ways of pairing branches in pointsA to branches in pointsB,
    # optionally with having them unpaired too (= paired to None)
    def allPairings(self, pointsA, pointsB):
        # One empty list, so return the other all unpaired:
        if len(pointsB) == 0:
            return [[(p, None) for p in pointsA]]
        if len(pointsA) == 0:
            return [[(None, p) for p in pointsB]]

        firstA, restA = pointsA[0], pointsA[1:]

        # Match the first in A with all the ones in B,
        #  and combine with  all matches of the remaining
        matchedA = []
        for iB, pB in enumerate(pointsB):
            for nextPairs in self.allPairings(restA, listWithoutIdx(pointsB, iB)):
                matchedA.append([(firstA, pB)] + nextPairs)

        # Otherwise, don't match the first of A, and combine with the rest
        unmatchedA = []
        for nextPairs in self.allPairings(restA, pointsB):
            unmatchedA.append([(firstA, None)] + nextPairs)

        # Note: return matched first, that's more likely to be a better match
        # and allow skipping future attempts.
        return matchedA + unmatchedA

    ###
    ### Matching calculations
    ###

    # Given two points, find the cost of combining them - defined as the
    #   difference in location relative to their previously matched siblings.
    def calcMatchCost(self, pointA, pointB, skipA, skipB):
        pointBeforeA = pointA.nextPointInBranch(-skipA, noWrap=False)
        pointBeforeB = pointB.nextPointInBranch(-skipB, noWrap=False)

        if pointBeforeA is not None:
            assert pointBeforeB is not None
            xA, yA, zA = self.treeA.worldCoordPoints([pointA, pointBeforeA])
            xB, yB, zB = self.treeB.worldCoordPoints([pointB, pointBeforeB])
            # Distance offset = | (pA-pbA) - (pB-pbB) |
            delta = [
                xA[0] - xA[1] - xB[0] + xB[1],
                yA[0] - yA[1] - yB[0] + yB[1],
                zA[0] - zA[1] - zB[0] + zB[1],
            ]
            return np.linalg.norm(np.array(delta))
        # Should be soma, so no cost for matching:
        return 0

    # Given a collection of next points to match, find the best pairing between
    #  them and return the score, plus the pairing.
    def calcBestPairing(self, nextPointsA, nextPointsB):
        bestPairingScore, bestPairingRun = np.inf, None

        for pairLists in self.allPairings(nextPointsA, nextPointsB):
            # Calculate how many we're skipping via unmatched children:
            nSkipped = 0
            for pair in pairLists:
                if pair[0] is not None and pair[1] is None:
                    nSkipped += self.subtreeCount('A', pair[0])
                elif pair[1] is not None and pair[0] is None:
                    nSkipped += self.subtreeCount('B', pair[1])

            # Cost too high, early exit
            pairingPenalty = nSkipped * self.unmatchedPenalty
            if bestPairingScore <= pairingPenalty:
                continue

            # Calculate the cost from matching the paired children:
            pairingScore, pairingRun = 0, []
            for pair in pairLists:
                if pair[0] is not None and pair[1] is not None:
                    pairingScore += self.recursiveMatch(pair[0], pair[1], 1, 1)
                    pairingRun.append((pair[0], pair[1], 1, 1))

            # Update best if better:
            totalScore = pairingScore + pairingPenalty
            if totalScore < bestPairingScore:
                bestPairingScore = totalScore
                bestPairingRun = pairingRun

        # No pairs, so costs nothing, and nothing to run
        if bestPairingRun is None:
            return 0, []
        else:
            return bestPairingScore, bestPairingRun

    # Calculate the best score when having either A or B unmatched.
    # Either:
    #   A was skipped (pointAorNext is a list, pointBorNext is a single point)
    #   B was skipped (pointAorNext is a single point, pointBorNext is a list)
    def calcBestSkip(self, pointAorNext, pointBorNext, skipA, skipB, bestScore):
        bestSkippingScore, bestSkippingRun = np.inf, None

        # Check that exactly one is a list:
        assert isinstance(pointAorNext, list) ^ isinstance(pointBorNext, list)
        nextPoints = pointAorNext if isinstance(pointAorNext, list) else pointBorNext
        nextTreeID = 'A' if isinstance(pointAorNext, list) else 'B'

        # Number of points down each next, and the total:
        nextPointCounts = [self.subtreeCount(nextTreeID, p) for p in nextPoints]
        allSkippedCount = np.sum(np.array(nextPointCounts))

        # See all next points to match - others are skipped:
        for nextPoint, dontSkipCount in zip(nextPoints, nextPointCounts):
            nSkipped = allSkippedCount - dontSkipCount + 1 # 1 for skipping this point too.
            skippingPenalty = nSkipped * self.unmatchedPenalty

            if bestSkippingScore <= skippingPenalty or bestScore <= skippingPenalty:
                continue # Too costly, early exit

            skippingScore, skippingRun = 0, []
            if isinstance(pointAorNext, list):
                # Try all next in A to match with B:
                skippingScore = self.recursiveMatch(nextPoint, pointBorNext, skipA + 1, skipB)
                skippingRun = [(nextPoint, pointBorNext, skipA + 1, skipB)]
            else:
                # Try all next in B to match with A:
                skippingScore = self.recursiveMatch(pointAorNext, nextPoint, skipA, skipB + 1)
                skippingRun = [(pointAorNext, nextPoint, skipA, skipB + 1)]

            # Check if better, and update.
            totalScore = skippingScore + skippingPenalty
            if totalScore < bestSkippingScore:
                bestSkippingScore = totalScore
                bestSkippingRun = skippingRun

        return bestSkippingScore, bestSkippingRun


    def recursiveMatch(self, pointA, pointB, skipA, skipB):
        # Check if results memoized:
        key = "%s:%s:%d:%d" % (pointA.id, pointB.id, skipA, skipB)
        if key in self.resultCache:
            return self.resultCache[key][0]

        nextPointsA = self.nextPoints('A', pointA)
        nextPointsB = self.nextPoints('B', pointB)

        # Option 1: Match A to B (Do this first as it's likely the best option)
        matchCost = self.calcMatchCost(pointA, pointB, skipA, skipB)
        bestPairingScore, bestPairingRun = self.calcBestPairing(nextPointsA, nextPointsB)
        bestScore = matchCost + bestPairingScore
        bestRunParams = [(pointA.id, pointB.id)] + bestPairingRun

        # Option 2: Try all the ways to skip point A:
        if skipA < self.maxSkip:
            skipScore, skipRunParams = self.calcBestSkip(nextPointsA, pointB, skipA, skipB, bestScore)
            if skipScore < bestScore:
                bestScore = skipScore
                bestRunParams = skipRunParams

        # Option 3: Try all the ways to skip point B:
        if skipB < self.maxSkip:
            skipScore, skipRunParams = self.calcBestSkip(pointA, nextPointsB, skipA, skipB, bestScore)
            if skipScore < bestScore:
                bestScore = skipScore
                bestRunParams = skipRunParams

        self.resultCache[key] = (bestScore, bestRunParams)
        if self.updateFunc is not None:
            self.updateFunc()
        return bestScore

    # Once roots are matched, walk the tree back along the optimal path to
    #   put the optimal matches into the result map.
    def extractResults(self, resultMap, pointA, pointB, skipA, skipB):
        key = "%s:%s:%d:%d" % (pointA.id, pointB.id, skipA, skipB)
        # Note: Results must have been calculated earlier:
        assert key in self.resultCache

        for params in self.resultCache[key][1]:
            if len(params) == 2:
                if params[0] != params[1]:
                    # treeB's old ID to new ID from treeA
                    resultMap[params[1]] = params[0]
            else:
                self.extractResults(resultMap, *params)

    # Actually run the matching
    def performAlignment(self, updateFunc=None):
        self.updateFunc = updateFunc

        rA = self.treeA.rootPoint
        rB = self.treeB.rootPoint

        # Recursively try everything...
        self.recursiveMatch(rA, rB, self.maxSkip, self.maxSkip)

        # Then extract the best:
        resultMap = {}
        self.extractResults(resultMap, rA, rB, self.maxSkip, self.maxSkip)
        return resultMap
