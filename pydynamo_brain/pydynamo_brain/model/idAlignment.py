import numpy as np

from typing import Any, Callable, Dict, List, Optional, Tuple

from pydynamo_brain.model import Tree, Point
from pydynamo_brain.model.tree.util import findNextPoints
from pydynamo_brain.util import listWithoutIdx

class IdAligner():
    # Two trees we're aligning:
    treeA: Tree
    treeB: Tree

    maxSkip: int = 3
    updateFunc: Optional[Callable[[], None]] = None
    unmatchedPenalty: float = 10

    # Memoized results
    resultCache: Dict[str, Tuple[float, Any]] = {}

    # Per-point property caches
    nextPointsCache: Dict[str, List[Point]] = {}
    subtreeSizeCache: Dict[str, int] = {}

    def __init__(self, treeA: Tree, treeB: Tree, maxSkip: int=3, unmatchedPenalty: float=10) -> None:
        self.treeA = treeA
        self.treeB = treeB
        self.maxSkip = maxSkip
        self.unmatchedPenalty = unmatchedPenalty
        self.resultCache = {}
        self.nextPointsCache = {}
        self.subtreeSizeCache = {}

        assert self.treeA.rootPoint is not None, "Can't align empty tree"
        assert self.treeB.rootPoint is not None, "Can't align empty tree"
        self.subtreeCount('A', self.treeA.rootPoint)
        self.subtreeCount('B', self.treeB.rootPoint)

    # Given a point, find all points one step down the tree:
    def nextPoints(self, treeID: str, point: Point) -> List[Point]:
        key = '%s:%s' % (treeID, point.id)
        if key not in self.nextPointsCache:
            self.nextPointsCache[key] = findNextPoints(point)
        return self.nextPointsCache[key]

    # Calculates the number of points in the subtree rooted at the given point.
    def subtreeCount(self, treeID: str, point: Point) -> int:
        key = '%s:%s' % (treeID, point.id)
        if key not in self.subtreeSizeCache:
            pointCount = 1
            for nextPoint in self.nextPoints(treeID, point):
                pointCount += self.subtreeCount(treeID, nextPoint)
            self.subtreeSizeCache[key] = pointCount
        return self.subtreeSizeCache[key]

    # Calculutes the max number of entries the cache can have.
    def maxCallCount(self) -> int:
        assert self.treeA.rootPoint is not None, "Can't align empty tree"
        assert self.treeB.rootPoint is not None, "Can't align empty tree"
        nA = self.subtreeCount('A', self.treeA.rootPoint)
        nB = self.subtreeCount('B', self.treeB.rootPoint)
        return nA * nB * self.maxSkip * self.maxSkip

    # Find all ways of pairing branches in pointsA to branches in pointsB,
    # optionally with having them unpaired too (= paired to None)
    def allPairings(
        self, pointsA: List[Point], pointsB: List[Point]
    ) -> List[List[Tuple[Optional[Point], Optional[Point]]]]:
        # One empty list, so return the other all unpaired:
        if len(pointsB) == 0:
            return [[(p, None) for p in pointsA]]
        if len(pointsA) == 0:
            return [[(None, p) for p in pointsB]]

        firstA, restA = pointsA[0], pointsA[1:]

        # Match the first in A with all the ones in B,
        #  and combine with  all matches of the remaining
        matchedA: List[List[Tuple[Optional[Point], Optional[Point]]]] = []

        optFirst: Optional[Point] = firstA
        for iB, pB in enumerate(pointsB):
            optB: Optional[Point] = pB
            for nextPairs in self.allPairings(restA, listWithoutIdx(pointsB, iB)):
                matchedA.append([(optFirst, optB)] + nextPairs)

        # Otherwise, don't match the first of A, and combine with the rest
        unmatchedA: List[List[Tuple[Optional[Point], Optional[Point]]]] = []
        for nextPairs in self.allPairings(restA, pointsB):
            optMissing: Optional[Point] = None
            unmatchedA.append([(optFirst, optMissing)] + nextPairs)

        # Note: return matched first, that's more likely to be a better match
        # and allow skipping future attempts.
        return matchedA + unmatchedA

    ###
    ### Matching calculations
    ###

    # Given two points, find the cost of combining them - defined as the
    #   difference in location relative to their previously matched siblings.
    def calcMatchCost(self, pointA: Point, pointB: Point, skipA: int, skipB: int) -> float:
        pointBeforeA = pointA.nextPointInBranch(-skipA, noWrap=False)
        pointBeforeB = pointB.nextPointInBranch(-skipB, noWrap=False)

        if pointBeforeA is not None:
            if pointBeforeB is not None:
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
        return 0.0

    # Given a collection of next points to match, find the best pairing between
    #  them and return the score, plus the pairing.
    def calcBestPairing(
        self, nextPointsA: List[Point], nextPointsB: List[Point]
    ) -> Tuple[float, List[Tuple[Point, Point, int, int]]]:
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
            pairingScore, pairingRun = 0.0, []
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
            emptyRun: List[Tuple[Point, Point, int, int]] = []
            return 0.0, emptyRun
        else:
            return bestPairingScore, bestPairingRun

    # Calculate the best score when having either A or B unmatched.
    # Either:
    #   A was skipped (pointAorNext is a list, pointBorNext is a single point)
    #   B was skipped (pointAorNext is a single point, pointBorNext is a list)
    def calcBestSkip(self,
        pointAorNext: Any, pointBorNext: Any, skipA: int, skipB: int, bestScore: float
    ) -> Tuple[float, Optional[Tuple[Point, Point, int, int]]]:
        bestSkippingScore: float = np.inf
        bestSkipNextParams: Optional[Tuple[Point, Point, int, int]] = None

        # Check that exactly one is a list:
        assert isinstance(pointAorNext, list) ^ isinstance(pointBorNext, list)
        nextPoints = pointAorNext if isinstance(pointAorNext, list) else pointBorNext
        nextTreeID = 'A' if isinstance(pointAorNext, list) else 'B'

        # Number of points down each next, and the total:
        nextPointCounts = [self.subtreeCount(nextTreeID, p) for p in nextPoints]
        allSkippedCount: int = sum(nextPointCounts)

        # See all next points to match - others are skipped:
        for nextPoint, dontSkipCount in zip(nextPoints, nextPointCounts):
            nSkipped = allSkippedCount - dontSkipCount + 1 # 1 for skipping this point too.
            skippingPenalty = nSkipped * self.unmatchedPenalty

            if bestSkippingScore <= skippingPenalty or bestScore <= skippingPenalty:
                continue # Too costly, early exit

            skippingScore: float = 0.0
            skippingNextParams: Optional[Tuple[Point, Point, int, int]] = None
            if isinstance(pointAorNext, list):
                # Try all next in A to match with B:
                skippingScore = self.recursiveMatch(nextPoint, pointBorNext, skipA + 1, skipB)
                skippingNextParams = (nextPoint, pointBorNext, skipA + 1, skipB)
            else:
                # Try all next in B to match with A:
                skippingScore = self.recursiveMatch(pointAorNext, nextPoint, skipA, skipB + 1)
                skippingNextParams = (pointAorNext, nextPoint, skipA, skipB + 1)

            # Check if better, and update.
            totalScore = skippingScore + skippingPenalty
            if totalScore < bestSkippingScore:
                bestSkippingScore = totalScore
                bestSkipNextParams = bestSkipNextParams

        return bestSkippingScore, bestSkipNextParams


    def recursiveMatch(self, pointA: Point, pointB: Point, skipA: int, skipB: int) -> float:
        # Check if results memoized:
        key = "%s:%s:%d:%d" % (pointA.id, pointB.id, skipA, skipB)
        if key in self.resultCache:
            return self.resultCache[key][0]

        # updateFunc returns True if interruption is needed
        if self.updateFunc is not None:
            if self.updateFunc():
                return np.inf

        nextPointsA = self.nextPoints('A', pointA)
        nextPointsB = self.nextPoints('B', pointB)

        # Option 1: Match A to B (Do this first as it's likely the best option)
        matchCost = self.calcMatchCost(pointA, pointB, skipA, skipB)
        bestPairingScore, bestPairingRun = self.calcBestPairing(nextPointsA, nextPointsB)
        bestScore = matchCost + bestPairingScore

        matchParams: List[Tuple[Point, Point, int, int]] = [(pointA, pointB, -1, -1)]
        bestRunParams = matchParams + bestPairingRun

        # Option 2: Try all the ways to skip point A:
        if skipA < self.maxSkip:
            skipScore, skipRunParams = self.calcBestSkip(nextPointsA, pointB, skipA, skipB, bestScore)
            if skipScore < bestScore and skipRunParams is not None:
                bestScore = skipScore
                bestRunParams = [skipRunParams]

        # Option 3: Try all the ways to skip point B:
        if skipB < self.maxSkip:
            skipScore, skipRunParams = self.calcBestSkip(pointA, nextPointsB, skipA, skipB, bestScore)
            if skipScore < bestScore and skipRunParams is not None:
                bestScore = skipScore
                bestRunParams = [skipRunParams]

        self.resultCache[key] = (bestScore, bestRunParams)
        return bestScore

    # Once roots are matched, walk the tree back along the optimal path to
    #   put the optimal matches into the result map.
    def extractResults(self,
        resultMap: Dict[str, str], pointA: Point, pointB: Point, skipA: int, skipB: int
    ) -> None:
        key = "%s:%s:%d:%d" % (pointA.id, pointB.id, skipA, skipB)
        # Note: Results must have been calculated earlier:
        assert key in self.resultCache

        for params in self.resultCache[key][1]:
            if params[2] == -1 and params[3] == -1: # [?, ?, -1, -1] used to indicate match
                if params[0] != params[1]:
                    # treeB's old ID to new ID from treeA
                    resultMap[params[1].id] = params[0].id
            else:
                self.extractResults(resultMap, *params)

    # Actually run the matching
    def performAlignment(self, updateFunc: Optional[Callable[[], None]]=None) -> Dict[str, str]:
        self.updateFunc = updateFunc

        rA = self.treeA.rootPoint
        rB = self.treeB.rootPoint

        if rA is None or rB is None:
            print ("Can't align empty trees")
            return {}

        # Recursively try everything...
        self.recursiveMatch(rA, rB, self.maxSkip, self.maxSkip)

        # Then extract the best:
        resultMap: Dict[str, str] = {}
        self.extractResults(resultMap, rA, rB, self.maxSkip, self.maxSkip)
        return resultMap
