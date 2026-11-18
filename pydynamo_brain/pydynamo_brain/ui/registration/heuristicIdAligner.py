"""Heuristic ID-only arbor registration (v2) for pyDynamo.

Aligns point and branch IDs between two traced dendritic trees (`treeA` -> `treeB`)
without moving 3D node coordinates:
  1. Anisotropy-weighted, 2-step smoothed minimal-angle branch canonicalization
  2. Linear focal/stage-drift estimation + swap-invariant Structural Fork matching
     across radial shells
  3. Free-tail, penalized-interior-gap 1D Markov step-vector DP along paired segments
  4. Multi-round unmatched outgoing sub-path wavefront recovery
"""

from __future__ import annotations

import copy
import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Sequence, Set, Tuple

import numpy as np
from scipy.optimize import linear_sum_assignment
from scipy.spatial.distance import cdist

from pydynamo_brain.model import FullState, Point, Tree


@dataclass
class HeuristicAlignmentResult:
    """Detailed output from `HeuristicIdAligner` for diagnostics and UI display."""

    remap: Dict[str, str]                                # {pointB_old_id: pointA_id}
    matched_pairs: List[Tuple[str, str, float, str]]     # [(idA, idB, cost_or_dist, stage)]
    matched_branch_points: List[Tuple[str, str, float]]  # [(bpA_id, bpB_id, drift_corrected_dist_um)]
    unmatched_bps_A: List[str]
    unmatched_bps_B: List[str]
    paired_segments: int
    added_points_B: List[str]
    removed_points_A: List[str]
    effective_bp_thresh_um: float
    effective_point_thresh_um: float
    elapsed_ms: float = 0.0


def sort_tree_branches_minimal_angle(tree: Tree, complete_multichild: bool = True) -> int:
    """Clean empty branches and canonicalize bifurcations by anisotropy-weighted,
    2-step smoothed minimal deflection angle (prevents discrete Z-slice stair-steps
    from flipping primary branch continuations).
    """
    n_cleaned = tree.cleanEmptyBranches()
    if not complete_multichild:
        tree.updateAllBranchesMinimalAngle()
        return n_cleaned

    if tree.rootPoint is None:
        return n_cleaned

    px = tree._fullState().projectOptions.pixelSizes
    wz = float(np.clip(np.sqrt(0.5 * (px[0] + px[1]) / max(px[2], 1e-6)), 0.35, 1.0))
    ms = np.array([1.0, 1.0, wz], dtype=float)

    def _deflection_angle(pt: Point, nxt: Optional[Point]) -> float:
        prev = pt.nextPointInBranch(delta=-1, noWrap=True)
        if prev is None or pt is None or nxt is None:
            return np.pi
        prev2 = prev.nextPointInBranch(delta=-1, noWrap=True) or prev
        nxt2 = nxt.nextPointInBranch(1, noWrap=True) or nxt
        xs, ys, zs = tree.worldCoordPoints([prev2, prev, pt, nxt, nxt2])
        pts = np.column_stack([xs, ys, zs]).astype(float) * ms[None, :]
        ab = 0.6 * (pts[2] - pts[1]) + 0.4 * (pts[2] - pts[0])
        bc = 0.6 * (pts[3] - pts[2]) + 0.4 * (pts[4] - pts[2])
        denom = float(np.linalg.norm(ab) * np.linalg.norm(bc))
        if denom < 1e-12:
            return 0.0
        return float(np.arccos(np.clip(np.dot(ab, bc) / denom, -1.0, 1.0)))

    visited: Set[str] = set()
    queue: List[Point] = [tree.rootPoint]
    while queue:
        pt = queue.pop(0)
        if pt is None or pt.id in visited:
            continue
        visited.add(pt.id)
        if not pt.isRoot() and len(pt.children) > 0:
            cur_nxt = pt.nextPointInBranch(1, noWrap=True)
            candidates = [] if cur_nxt is None else [(_deflection_angle(pt, cur_nxt), None, cur_nxt)]
            for ch in pt.children:
                if len(ch.points) > 0:
                    candidates.append((_deflection_angle(pt, ch.points[0]), ch, ch.points[0]))
            if candidates:
                candidates.sort(key=lambda item: item[0])
                _, best_ch, best_pt = candidates[0]
                if best_ch is not None:
                    tree.continueParentBranchIfFirst(best_pt)
            pt.children = [ch for ch in pt.children if len(ch.points) > 0]
            pt.children.sort(key=lambda ch: _deflection_angle(pt, ch.points[0]))

        nxt = pt.nextPointInBranch(1, noWrap=True)
        if nxt is not None:
            queue.append(nxt)
        for ch in pt.children:
            if len(ch.points) > 0:
                queue.append(ch.points[0])

    return n_cleaned


def root_centered_world_coords(tree: Tree, points: Sequence[Point], use_world_um: bool = True) -> np.ndarray:
    """Return `(N, 3)` coordinates with `tree.rootPoint` centered at `(0, 0, 0)`."""
    if tree.rootPoint is None or len(points) == 0:
        return np.zeros((0, 3), dtype=float)
    if use_world_um:
        rx, ry, rz = tree.worldCoordPoints([tree.rootPoint])
        root_xyz = np.array([rx[0], ry[0], rz[0]], dtype=float)
        xs, ys, zs = tree.worldCoordPoints(list(points))
        coords = np.column_stack([xs, ys, zs]).astype(float)
    else:
        root_xyz = np.asarray(tree.rootPoint.location, dtype=float)
        coords = np.asarray([p.location for p in points], dtype=float)
    return coords - root_xyz


def _subtree_cable_length(pt: Point, cmap: Dict[str, np.ndarray], cache: Dict[str, float]) -> float:
    if pt.id in cache:
        return cache[pt.id]
    total = 0.0
    nxt = pt.nextPointInBranch(1, noWrap=True)
    if nxt is not None:
        total += float(np.linalg.norm(cmap[nxt.id] - cmap[pt.id])) + _subtree_cable_length(nxt, cmap, cache)
    for ch in pt.children:
        if ch.points:
            c0 = ch.points[0]
            total += float(np.linalg.norm(cmap[c0.id] - cmap[pt.id])) + _subtree_cable_length(c0, cmap, cache)
    cache[pt.id] = total
    return total


def _outgoing_arm_info(
    pt: Point,
    cmap_dir: Dict[str, np.ndarray],
    cmap_um: Dict[str, np.ndarray],
    cable_um: Dict[str, float],
    lookahead: int = 4,
) -> List[Tuple[float, np.ndarray, Point]]:
    """Return `(arm_cable_um, unit_dir_3d, first_point)` for all outgoing paths (swap-invariant)."""
    p_um = cmap_um[pt.id]
    p_dir = cmap_dir[pt.id]
    starts: List[Point] = []
    if not pt.isRoot():
        nxt = pt.nextPointInBranch(1, noWrap=True)
        if nxt is not None:
            starts.append(nxt)
    for ch in pt.children:
        if ch.points:
            starts.append(ch.points[0])

    arms: List[Tuple[float, np.ndarray, Point]] = []
    for st_p in starts:
        arm_len = float(np.linalg.norm(cmap_um[st_p.id] - p_um)) + cable_um[st_p.id]
        vecs = []
        cur: Optional[Point] = st_p
        for _ in range(lookahead):
            if cur is None:
                break
            vecs.append(cmap_dir[cur.id] - p_dir)
            cur = cur.nextPointInBranch(1, noWrap=True)
        mv = np.mean(vecs, axis=0)
        nv = float(np.linalg.norm(mv))
        arms.append((arm_len, mv / nv if nv > 1e-9 else np.zeros(3), st_p))
    return arms


def _ray_set_distance(raysA: List[np.ndarray], raysB: List[np.ndarray]) -> float:
    """Swap-invariant angular distance between outgoing ray sets at two candidate forks."""
    if not raysA or not raysB:
        return 1.0
    cost = 1.0 - np.clip(np.vstack(raysA) @ np.vstack(raysB).T, -1.0, 1.0)
    ri, ci = linear_sum_assignment(cost)
    return float(np.mean(cost[ri, ci]))


def _walk_pos_only(
    ptsA: Sequence[Point],
    ptsB: Sequence[Point],
    cA: np.ndarray,
    cB: np.ndarray,
    point_thresh: float,
) -> List[Tuple[Point, Point, float]]:
    """Position-only monotonic branch walk."""
    m, n = len(ptsA), len(ptsB)
    if m == 0 or n == 0:
        return []
    dists = cdist(cA, cB)
    dp = np.zeros((m + 1, n + 1), dtype=float)
    back = np.zeros((m + 1, n + 1), dtype=np.int8)
    back[1:, 0] = 2
    back[0, 1:] = 3
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if dp[i - 1, j] >= dp[i, j - 1]:
                best = dp[i - 1, j]
                op = 2
            else:
                best = dp[i, j - 1]
                op = 3
            d = dists[i - 1, j - 1]
            if d <= point_thresh:
                cand = dp[i - 1, j - 1] + (2.0 * point_thresh - d)
                if cand > best:
                    best = cand
                    op = 1
            dp[i, j] = best
            back[i, j] = op
    out: List[Tuple[Point, Point, float]] = []
    i, j = m, n
    while i > 0 and j > 0:
        if back[i, j] == 1:
            out.append((ptsA[i - 1], ptsB[j - 1], float(dists[i - 1, j - 1])))
            i -= 1
            j -= 1
        elif back[i, j] == 2:
            i -= 1
        else:
            j -= 1
    out.reverse()
    return out


def _walk_paper_step_cost_1d(
    ptsA: Sequence[Point],
    ptsB: Sequence[Point],
    anchorA_start: np.ndarray,
    anchorB_start: np.ndarray,
    rawA: np.ndarray,
    rawB: np.ndarray,
    anchorA_end: Optional[np.ndarray] = None,
    anchorB_end: Optional[np.ndarray] = None,
    max_skip: int = 3,
    unmatched_penalty: float = 2.8,
    pt_thresh: Optional[float] = None,
) -> List[Tuple[Point, Point, float]]:
    """Free-tail, penalized-interior-gap 1D Markov Step-Vector Aligner.

    Uses local step-vector conservation `||(pA[i]-pA[pi]) - (pB[j]-pB[pj])||`
    combined with a drift-interpolated proximity gate. Interior skips along a
    shaft are penalized while open distal branch tails can terminate freely,
    preventing distal tip growth from stretching upstream node correspondences.
    """
    m, n = len(ptsA), len(ptsB)
    if m == 0 or n == 0:
        return []

    if pt_thresh is None:
        pt_thresh = unmatched_penalty / 0.55

    fullA = np.vstack([anchorA_start[None, :], rawA])
    fullB = np.vstack([anchorB_start[None, :], rawB])

    d_start = anchorB_start - anchorA_start
    if anchorA_end is not None and anchorB_end is not None:
        segA = np.linalg.norm(np.diff(fullA, axis=0), axis=1)
        cumA = np.concatenate([[0.0], np.cumsum(segA)])
        totA = cumA[-1] + float(np.linalg.norm(anchorA_end - fullA[-1]))
        sA = cumA / max(totA, 1e-6)
        d_end = anchorB_end - anchorA_end
        expected_B = fullA + (1.0 - sA[:, None]) * d_start[None, :] + sA[:, None] * d_end[None, :]
    else:
        expected_B = fullA + d_start[None, :]

    pos_err = cdist(expected_B[1:], fullB[1:])
    reward_match = 0.72 * pt_thresh
    interior_skip_pen = 0.88 * pt_thresh
    pos_gate = 1.65 * pt_thresh if anchorA_end is None else 2.30 * pt_thresh

    NEG_INF = -1e12
    dp = np.full((m + 1, n + 1), NEG_INF, dtype=float)
    prev_ptr = np.full((m + 1, n + 1, 2), -1, dtype=int)
    dp[0, 0] = 0.0

    for i in range(1, m + 1):
        i_lo = max(0, i - max_skip)
        dA_all = fullA[i] - fullA[i_lo:i]
        skip_i = (i - 1) - np.arange(i_lo, i)
        for j in range(1, n + 1):
            pe = pos_err[i - 1, j - 1]
            if pe > pos_gate:
                continue
            j_lo = max(0, j - max_skip)
            dp_sub = dp[i_lo:i, j_lo:j]
            if np.max(dp_sub) <= NEG_INF / 2:
                continue
            dB_all = fullB[j] - fullB[j_lo:j]
            skip_j = (j - 1) - np.arange(j_lo, j)

            step_err = np.linalg.norm(dA_all[:, None, :] - dB_all[None, :, :], axis=2)
            gain = (
                reward_match
                - (0.82 * step_err + 0.18 * pe)
                - (skip_i[:, None] + skip_j[None, :]) * interior_skip_pen
            )
            cand = dp_sub + gain

            flat_idx = int(np.argmax(cand))
            best_val = float(cand.flat[flat_idx])
            if best_val > NEG_INF / 2:
                ri, cj = divmod(flat_idx, cand.shape[1])
                dp[i, j] = best_val
                prev_ptr[i, j, 0] = i_lo + ri
                prev_ptr[i, j, 1] = j_lo + cj

    if anchorA_end is not None and anchorB_end is not None:
        best_sc = (
            -0.82 * float(np.linalg.norm((anchorA_end - anchorA_start) - (anchorB_end - anchorB_start)))
            - (m + n) * interior_skip_pen
        )
        end_i, end_j = 0, 0
        for i in range(max(1, m + 1 - max_skip), m + 1):
            for j in range(max(1, n + 1 - max_skip), n + 1):
                if dp[i, j] <= NEG_INF / 2:
                    continue
                cl = float(np.linalg.norm((anchorA_end - fullA[i]) - (anchorB_end - fullB[j])))
                sc = dp[i, j] - 0.82 * cl - ((m - i) + (n - j)) * interior_skip_pen
                if sc > best_sc:
                    best_sc = sc
                    end_i, end_j = i, j
    else:
        best_sc = 0.0
        end_i, end_j = 0, 0
        mf = int(np.argmax(dp[1:, 1:]))
        val = float(dp[1:, 1:].flat[mf])
        if val > best_sc:
            ei, ej = divmod(mf, n)
            end_i, end_j = ei + 1, ej + 1

    out: List[Tuple[Point, Point, float]] = []
    ci, cj = end_i, end_j
    while ci > 0 and cj > 0:
        pi, pj = int(prev_ptr[ci, cj, 0]), int(prev_ptr[ci, cj, 1])
        if pi < 0 or pj < 0:
            break
        err = float(np.linalg.norm((fullA[ci] - fullA[pi]) - (fullB[cj] - fullB[pj])))
        out.append((ptsA[ci - 1], ptsB[cj - 1], err))
        ci, cj = pi, pj
    out.reverse()
    return out


class HeuristicIdAligner:
    """Fast heuristic ID aligner (v2) for pyDynamo dendritic trees:
      1. Anisotropy-weighted, smoothed minimal-angle branch canonicalization
      2. Linear focal/stage-drift correction + swap-invariant Structural Fork landmarks
      3. Free-tail, penalized-interior-gap 1D Markov step-vector DP along paired segments
      4. Multi-round unmatched outgoing sub-path wavefront recovery
    """

    def __init__(
        self,
        treeA: Tree,
        treeB: Tree,
        branchPointThreshold: float = 5.0,
        pointThreshold: float = 5.0,
        coreArmLengthUm: float = 6.0,
        maxSkip: int = 3,
        autoScale: bool = True,
        hierarchicalDrift: bool = True,
        walkMode: str = "paper_step",
        subbranchRecovery: bool = True,
        completeMultiChildAngle: bool = True,
        useWorldCoords: bool = True,
    ) -> None:
        assert treeA.rootPoint is not None, "Can't align empty reference treeA"
        assert treeB.rootPoint is not None, "Can't align empty target treeB"
        self.treeA = treeA
        self.treeB = treeB
        self.branchPointThreshold = branchPointThreshold
        self.pointThreshold = pointThreshold
        self.coreArmLengthUm = coreArmLengthUm
        self.maxSkip = maxSkip
        self.autoScale = autoScale
        self.hierarchicalDrift = hierarchicalDrift
        self.walkMode = walkMode
        self.subbranchRecovery = subbranchRecovery
        self.completeMultiChildAngle = completeMultiChildAngle
        self.useWorldCoords = useWorldCoords

    def maxCallCount(self) -> int:
        """Number of pipeline stages reported to UI progress listeners."""
        return 4

    @staticmethod
    def _outgoing_segments(
        tree: Tree,
        bp: Point,
        stop_bp_ids: Set[str],
        cmap_um: Optional[Dict[str, np.ndarray]] = None,
        cab_um: Optional[Dict[str, float]] = None,
        min_arm_um: float = 0.0,
    ) -> List[Tuple[List[Point], Optional[Point]]]:
        starts: List[Point] = []
        if not bp.isRoot():
            nxt = bp.nextPointInBranch(1, noWrap=True)
            if nxt is not None:
                starts.append(nxt)
        for ch in bp.children:
            if ch.points:
                c0 = ch.points[0]
                if bp.isRoot() or min_arm_um <= 0.0 or cmap_um is None or cab_um is None:
                    starts.append(c0)
                elif (float(np.linalg.norm(cmap_um[c0.id] - cmap_um[bp.id])) + cab_um[c0.id]) >= min_arm_um:
                    starts.append(c0)

        segs: List[Tuple[List[Point], Optional[Point]]] = []
        for st_pt in starts:
            interior: List[Point] = []
            end_bp: Optional[Point] = None
            cur: Optional[Point] = st_pt
            while cur is not None:
                if cur.id in stop_bp_ids:
                    end_bp = cur
                    break
                interior.append(cur)
                cur = cur.nextPointInBranch(1, noWrap=True)
            segs.append((interior, end_bp))
        return segs

    @staticmethod
    def _unmatched_subpaths(tree: Tree, used_ids: Set[str]) -> List[Tuple[Point, List[Point]]]:
        out: List[Tuple[Point, List[Point]]] = []
        for pt in tree.flattenPoints():
            if pt.id not in used_ids:
                continue
            starts = ([] if pt.isRoot() else [pt.nextPointInBranch(1, noWrap=True)]) + [
                c.points[0] for c in pt.children if c.points
            ]
            for st_p in [x for x in starts if x is not None and x.id not in used_ids]:
                seg: List[Point] = []
                cur: Optional[Point] = st_p
                while cur is not None and cur.id not in used_ids:
                    seg.append(cur)
                    cur = cur.nextPointInBranch(1, noWrap=True)
                if seg:
                    out.append((pt, seg))
        return out

    def performAlignmentDetailed(
        self,
        updateFunc: Optional[Callable[[], Optional[bool]]] = None,
    ) -> HeuristicAlignmentResult:
        """Run the 4-stage heuristic ID alignment and return detailed diagnostics."""
        t_start = time.perf_counter()

        def _check_cancelled() -> bool:
            return bool(updateFunc is not None and updateFunc())

        def _empty_result() -> HeuristicAlignmentResult:
            return HeuristicAlignmentResult(
                remap={},
                matched_pairs=[],
                matched_branch_points=[],
                unmatched_bps_A=[],
                unmatched_bps_B=[],
                paired_segments=0,
                added_points_B=[],
                removed_points_A=[],
                effective_bp_thresh_um=float(self.branchPointThreshold),
                effective_point_thresh_um=float(self.pointThreshold),
                elapsed_ms=(time.perf_counter() - t_start) * 1000.0,
            )

        tA = copy.deepcopy(self.treeA)
        tB = copy.deepcopy(self.treeB)
        tA._parentState = self.treeA._parentState
        tB._parentState = self.treeB._parentState

        # Stage 1: Minimal-angle branch canonicalization on working copies
        sort_tree_branches_minimal_angle(tA, complete_multichild=self.completeMultiChildAngle)
        sort_tree_branches_minimal_angle(tB, complete_multichild=self.completeMultiChildAngle)
        if _check_cancelled():
            return _empty_result()

        assert tA.rootPoint is not None and tB.rootPoint is not None
        ptsA = tA.flattenPoints()
        ptsB = tB.flattenPoints()
        arrA_um = root_centered_world_coords(tA, ptsA, use_world_um=self.useWorldCoords)
        arrB_um = root_centered_world_coords(tB, ptsB, use_world_um=self.useWorldCoords)
        cmapA_um = {ptsA[i].id: arrA_um[i] for i in range(len(ptsA))}
        cmapB_um = {ptsB[i].id: arrB_um[i] for i in range(len(ptsB))}

        cabA: Dict[str, float] = {}
        cabB: Dict[str, float] = {}
        for p in reversed(ptsA):
            _subtree_cable_length(p, cmapA_um, cabA)
        for p in reversed(ptsB):
            _subtree_cable_length(p, cmapB_um, cabB)

        # Axial Z-slice quantization weight & linear stage/focus drift correction
        if self.hierarchicalDrift and self.useWorldCoords:
            px = tA._fullState().projectOptions.pixelSizes
            wz = float(np.clip(np.sqrt(0.5 * (px[0] + px[1]) / max(px[2], 1e-6)), 0.35, 1.0))
            metric_scale = np.array([1.0, 1.0, wz], dtype=float)

            core_mask_A = np.array([not p.isRoot() and cabA[p.id] >= self.coreArmLengthUm for p in ptsA])
            core_mask_B = np.array([not p.isRoot() and cabB[p.id] >= self.coreArmLengthUm for p in ptsB])
            cA_core = arrA_um[core_mask_A] if np.any(core_mask_A) else arrA_um
            cB_core = arrB_um[core_mask_B] if np.any(core_mask_B) else arrB_um

            arrA_corr = arrA_um.copy()
            if len(cA_core) >= 12 and len(cB_core) >= 12:
                cur_A = cA_core.copy()
                for it in range(4):
                    dmat = cdist(cur_A * metric_scale, cB_core * metric_scale)
                    nn_ab = np.argmin(dmat, axis=1)
                    nn_ba = np.argmin(dmat, axis=0)
                    pairs_idx = [
                        (i, int(nn_ab[i]), dmat[i, nn_ab[i]])
                        for i in range(len(cur_A))
                        if nn_ba[nn_ab[i]] == i
                    ]
                    if len(pairs_idx) < 10:
                        break
                    pairs_idx.sort(key=lambda x: x[2])
                    keep = pairs_idx[: max(10, int(0.70 * len(pairs_idx)))]
                    src = cA_core[[i for i, _, _ in keep]]
                    dst = cB_core[[j for _, j, _ in keep]]
                    if it == 0:
                        shift = np.median(dst - src, axis=0)
                        if np.linalg.norm(shift) <= 8.0:
                            cur_A = cA_core + shift[None, :]
                            arrA_corr = arrA_um + shift[None, :]
                    else:
                        X_aug = np.column_stack([src, np.ones(len(src))])
                        Y_res = dst - src
                        reg = np.diag([400.0, 400.0, 400.0, 0.5])
                        W_coef = np.linalg.solve(X_aug.T @ X_aug + reg, X_aug.T @ Y_res)
                        if np.linalg.norm(W_coef[:3], ord=2) <= 0.22 and np.linalg.norm(W_coef[3]) <= 10.0:
                            cur_A = cA_core + np.column_stack([cA_core, np.ones(len(cA_core))]) @ W_coef
                            arrA_corr = arrA_um + np.column_stack([arrA_um, np.ones(len(arrA_um))]) @ W_coef

            arrA = arrA_corr * metric_scale[None, :]
            arrB = arrB_um * metric_scale[None, :]
        else:
            core_mask_A = np.array([not p.isRoot() for p in ptsA])
            core_mask_B = np.array([not p.isRoot() for p in ptsB])
            arrA = arrA_um
            arrB = arrB_um

        cmapA = {ptsA[i].id: arrA[i] for i in range(len(ptsA))}
        cmapB = {ptsB[i].id: arrB[i] for i in range(len(ptsB))}

        all_bpsA = [p for p in ptsA if not p.isRoot() and len(p.children) > 0]
        all_bpsB = [p for p in ptsB if not p.isRoot() and len(p.children) > 0]

        bp_thresh = float(self.branchPointThreshold)
        pt_thresh = float(self.pointThreshold)
        if self.autoScale and np.any(core_mask_A) and np.any(core_mask_B):
            c_xyzA = arrA[core_mask_A]
            c_xyzB = arrB[core_mask_B]
            if len(c_xyzA) >= 5 and len(c_xyzB) >= 5:
                dc = cdist(c_xyzA, c_xyzB)
                cdrift = float(np.percentile(np.concatenate([dc.min(axis=1), dc.min(axis=0)]), 45))
                bp_thresh = float(np.clip(2.6 * cdrift + 1.4, 3.6, 12.5))
                pt_thresh = float(np.clip(2.2 * cdrift + 1.6, 3.8, 10.5))

        # Stage 2: Branch-Point Matching
        matched_bps: List[Tuple[Point, Point, float]] = [(tA.rootPoint, tB.rootPoint, 0.0)]
        matched_bp_records: List[Tuple[str, str, float]] = []
        matched_pairs: List[Tuple[str, str, float, str]] = [(tA.rootPoint.id, tB.rootPoint.id, 0.0, "root")]
        drift_at_A: Dict[str, np.ndarray] = {tA.rootPoint.id: np.zeros(3, dtype=float)}

        if all_bpsA and all_bpsB:
            if not self.hierarchicalDrift:
                cA_bp = np.array([cmapA[p.id] for p in all_bpsA])
                cB_bp = np.array([cmapB[p.id] for p in all_bpsB])
                dmat = cdist(cA_bp, cB_bp)
                r_idx, c_idx = linear_sum_assignment(np.where(dmat <= bp_thresh, dmat, 1e9))
                for ri, ci in zip(r_idx, c_idx):
                    d = float(dmat[ri, ci])
                    if d <= bp_thresh:
                        matched_bps.append((all_bpsA[ri], all_bpsB[ci], d))
                        matched_bp_records.append((all_bpsA[ri].id, all_bpsB[ci].id, d))
                        matched_pairs.append((all_bpsA[ri].id, all_bpsB[ci].id, d, "branch_point"))
                        drift_at_A[all_bpsA[ri].id] = cmapB[all_bpsB[ci].id] - cmapA[all_bpsA[ri].id]
            else:
                armsA_all = {p.id: _outgoing_arm_info(p, cmapA, cmapA_um, cabA) for p in all_bpsA}
                armsB_all = {p.id: _outgoing_arm_info(p, cmapB, cmapB_um, cabB) for p in all_bpsB}
                core_bpsA = [
                    p for p in all_bpsA
                    if sum(1 for ln, _, _ in armsA_all[p.id] if ln >= self.coreArmLengthUm) >= 2
                ]
                core_bpsB = [
                    p for p in all_bpsB
                    if sum(1 for ln, _, _ in armsB_all[p.id] if ln >= self.coreArmLengthUm) >= 2
                ]
                if len(core_bpsA) < 3 or len(core_bpsB) < 3:
                    core_bpsA, core_bpsB = all_bpsA, all_bpsB

                def _in_tan(pt: Point, cm: Dict[str, np.ndarray]) -> np.ndarray:
                    cur = pt
                    for _ in range(4):
                        c = cur.nextPointInBranch(-1, noWrap=False)
                        if c is None:
                            break
                        cur = c
                    v = cm[pt.id] - cm[cur.id]
                    nv = float(np.linalg.norm(v))
                    return v / nv if nv > 1e-9 else np.zeros(3)

                in_tanA = {p.id: _in_tan(p, cmapA) for p in core_bpsA}
                in_tanB = {p.id: _in_tan(p, cmapB) for p in core_bpsB}
                raysA = {
                    p.id: [u for ln, u, _ in armsA_all[p.id] if ln >= self.coreArmLengthUm]
                    or [u for _, u, _ in armsA_all[p.id]]
                    for p in core_bpsA
                }
                raysB = {
                    p.id: [u for ln, u, _ in armsB_all[p.id] if ln >= self.coreArmLengthUm]
                    or [u for _, u, _ in armsB_all[p.id]]
                    for p in core_bpsB
                }

                radiiA = np.array([np.linalg.norm(cmapA[p.id]) for p in core_bpsA])
                shell_edges = np.linspace(0.0, float(radiiA.max()) + 1.0, 5)
                used_B: Set[int] = set()
                anchor_pos_A = [np.zeros(3)]
                anchor_drifts = [np.zeros(3)]

                for sh_i in range(len(shell_edges) - 1):
                    r_lo, r_hi = shell_edges[sh_i], shell_edges[sh_i + 1]
                    cand_A = [i for i, r in enumerate(radiiA) if r_lo <= r < r_hi]
                    cand_B = [j for j in range(len(core_bpsB)) if j not in used_B]
                    if not cand_A or not cand_B:
                        continue

                    anc_arr = np.vstack(anchor_pos_A)
                    drf_arr = np.vstack(anchor_drifts)
                    cost_mat = np.full((len(cand_A), len(cand_B)), 1e9, dtype=float)
                    raw_d_mat = np.zeros((len(cand_A), len(cand_B)), dtype=float)

                    for rk, ia in enumerate(cand_A):
                        pA = core_bpsA[ia]
                        posA = cmapA[pA.id]
                        anc_drift = np.zeros(3)
                        cur_up = pA.nextPointInBranch(-1, noWrap=False)
                        while cur_up is not None:
                            if cur_up.id in drift_at_A:
                                anc_drift = drift_at_A[cur_up.id]
                                break
                            cur_up = cur_up.nextPointInBranch(-1, noWrap=False)

                        weights = 1.0 / (np.linalg.norm(anc_arr - posA[None, :], axis=1) + 8.0) ** 2
                        spatial_drift = (weights[:, None] * drf_arr).sum(axis=0) / weights.sum()
                        pred_posB = posA + 0.65 * anc_drift + 0.35 * spatial_drift

                        for ck, ib in enumerate(cand_B):
                            pB = core_bpsB[ib]
                            d_sp = float(np.linalg.norm(cmapB[pB.id] - pred_posB))
                            raw_d_mat[rk, ck] = d_sp
                            if d_sp > bp_thresh:
                                continue
                            cos_in = float(np.dot(in_tanA[pA.id], in_tanB[pB.id]))
                            if cos_in < 0.30:
                                continue
                            r_dist = _ray_set_distance(raysA[pA.id], raysB[pB.id])
                            if r_dist > 0.65:
                                continue
                            ratio_pen = abs(np.log((cabA[pA.id] + 5.0) / (cabB[pB.id] + 5.0))) * 0.8
                            cost_mat[rk, ck] = d_sp + (1.0 - cos_in) * 1.2 + r_dist * 1.6 + ratio_pen

                    for rk, ck in zip(*linear_sum_assignment(cost_mat)):
                        if cost_mat[rk, ck] < 1e8:
                            ia, ib = cand_A[rk], cand_B[ck]
                            pA, pB = core_bpsA[ia], core_bpsB[ib]
                            d_val = float(raw_d_mat[rk, ck])
                            matched_bps.append((pA, pB, d_val))
                            matched_bp_records.append((pA.id, pB.id, d_val))
                            matched_pairs.append((pA.id, pB.id, d_val, "branch_point"))
                            used_B.add(ib)
                            dv = cmapB[pB.id] - cmapA[pA.id]
                            drift_at_A[pA.id] = dv
                            anchor_pos_A.append(cmapA[pA.id])
                            anchor_drifts.append(dv)

        if _check_cancelled():
            return _empty_result()

        bp_map_AtoB = {pA.id: pB for pA, pB, _ in matched_bps}
        matched_bp_ids_A = set(bp_map_AtoB.keys())
        matched_bp_ids_B = {pB.id for _, pB, _ in matched_bps}
        unmatched_bps_A = [p.id for p in all_bpsA if p.id not in matched_bp_ids_A]
        unmatched_bps_B = [p.id for p in all_bpsB if p.id not in matched_bp_ids_B]

        # Stage 3: Pair Structural Outgoing Segments & Run Free-Tail 1D Step-Vector DP
        used_pts_A = set(matched_bp_ids_A)
        used_pts_B = set(matched_bp_ids_B)
        n_paired_segments = 0
        min_seg_arm = self.coreArmLengthUm * 0.75 if self.hierarchicalDrift else 0.0

        for bpA, bpB, _ in matched_bps:
            segsA = self._outgoing_segments(tA, bpA, matched_bp_ids_A, cmapA_um, cabA, min_seg_arm)
            segsB = self._outgoing_segments(tB, bpB, matched_bp_ids_B, cmapB_um, cabB, min_seg_arm)
            if not segsA or not segsB:
                continue
            origA, origB = cmapA[bpA.id], cmapB[bpB.id]
            b_start_th = max(bp_thresh + 1.5, pt_thresh * 1.25)

            scost = np.full((len(segsA), len(segsB)), 1e9, dtype=float)
            for ia, (intA, endA) in enumerate(segsA):
                pts_look_A = intA[:4] + ([endA] if endA is not None and len(intA) < 4 else [])
                if not pts_look_A:
                    continue
                vA = np.vstack([cmapA[p.id] - origA for p in pts_look_A])
                dA = vA.mean(axis=0)
                nA = float(np.linalg.norm(dA))
                for ib, (intB, endB) in enumerate(segsB):
                    pts_look_B = intB[:4] + ([endB] if endB is not None and len(intB) < 4 else [])
                    if not pts_look_B:
                        continue
                    if endA is not None and endB is not None:
                        if bp_map_AtoB.get(endA.id) is not None and bp_map_AtoB[endA.id].id == endB.id:
                            scost[ia, ib] = 0.01
                        continue
                    vB = np.vstack([cmapB[p.id] - origB for p in pts_look_B])
                    dB = vB.mean(axis=0)
                    nB = float(np.linalg.norm(dB))
                    if (
                        self.hierarchicalDrift
                        and nA > 1e-6
                        and nB > 1e-6
                        and float(np.dot(dA / nA, dB / nB)) < 0.35
                    ):
                        continue
                    k = min(len(vA), len(vB))
                    d = 0.5 * float(np.linalg.norm(vA[0] - vB[0])) + 0.5 * float(
                        np.linalg.norm(vA[:k].mean(axis=0) - vB[:k].mean(axis=0))
                    )
                    if d <= b_start_th:
                        scost[ia, ib] = max(d, 0.02)

            for ia, ib in zip(*linear_sum_assignment(scost)):
                if scost[ia, ib] >= 1e8:
                    continue
                n_paired_segments += 1
                intA, endA = segsA[ia]
                intB, endB = segsB[ib]
                wA = [p for p in intA if p.id not in used_pts_A]
                wB = [p for p in intB if p.id not in used_pts_B]
                if not wA or not wB:
                    continue
                rawA = np.vstack([cmapA[p.id] for p in wA])
                rawB = np.vstack([cmapB[p.id] for p in wB])

                if self.walkMode == "pos":
                    pairs = _walk_pos_only(wA, wB, rawA - origA, rawB - origB, pt_thresh)
                else:
                    both = (
                        endA is not None
                        and endB is not None
                        and bp_map_AtoB.get(endA.id) is not None
                        and bp_map_AtoB[endA.id].id == endB.id
                    )
                    pairs = _walk_paper_step_cost_1d(
                        wA,
                        wB,
                        origA,
                        origB,
                        rawA,
                        rawB,
                        anchorA_end=cmapA[endA.id] if both else None,
                        anchorB_end=cmapB[endB.id] if both else None,
                        max_skip=self.maxSkip,
                        pt_thresh=pt_thresh,
                    )
                for pA, pB, err in pairs:
                    used_pts_A.add(pA.id)
                    used_pts_B.add(pB.id)
                    matched_pairs.append((pA.id, pB.id, err, "branch_walk"))

        if _check_cancelled():
            return _empty_result()

        # Stage 4: Multi-round Unmatched Outgoing Sub-Path Wavefront Recovery
        if self.subbranchRecovery:
            for _ in range(5):
                map_all = {idA: idB for idA, idB, _, _ in matched_pairs}
                upA = self._unmatched_subpaths(tA, used_pts_A)
                upB = self._unmatched_subpaths(tB, used_pts_B)
                if not upA or not upB:
                    break
                rcost = np.full((len(upA), len(upB)), 1e9, dtype=float)
                for ia, (parA, segA) in enumerate(upA):
                    if parA.id not in map_all:
                        continue
                    pred_parB = cmapA[parA.id] + (cmapB[map_all[parA.id]] - cmapA[parA.id])
                    kA = min(4, len(segA))
                    rvA = np.vstack([cmapA[p.id] - cmapA[parA.id] for p in segA[:kA]])
                    dA = rvA.mean(axis=0)
                    nA = float(np.linalg.norm(dA))
                    for ib, (parB, segB) in enumerate(upB):
                        d_par = float(np.linalg.norm(cmapB[parB.id] - pred_parB))
                        if d_par > min(bp_thresh, 4.8):
                            continue
                        kB = min(4, len(segB))
                        k = min(kA, kB)
                        rvB = np.vstack([cmapB[p.id] - cmapB[parB.id] for p in segB[:kB]])
                        dB = rvB.mean(axis=0)
                        nB = float(np.linalg.norm(dB))
                        if nA > 1e-6 and nB > 1e-6 and float(np.dot(dA / nA, dB / nB)) < 0.25:
                            continue
                        d_dir = float(np.linalg.norm(rvA[:k].mean(axis=0) - rvB[:k].mean(axis=0)))
                        if d_dir <= pt_thresh * 1.15:
                            rcost[ia, ib] = d_par + d_dir

                added_any = False
                for ia, ib in zip(*linear_sum_assignment(rcost)):
                    if rcost[ia, ib] >= 1e8:
                        continue
                    parA, segA = upA[ia]
                    parB, segB = upB[ib]
                    n_paired_segments += 1
                    rawA = np.vstack([cmapA[p.id] for p in segA])
                    rawB = np.vstack([cmapB[p.id] for p in segB])
                    if self.walkMode == "pos":
                        pairs = _walk_pos_only(
                            segA, segB, rawA - cmapA[parA.id], rawB - cmapB[parB.id], pt_thresh
                        )
                    else:
                        pairs = _walk_paper_step_cost_1d(
                            segA,
                            segB,
                            cmapA[parA.id],
                            cmapB[parB.id],
                            rawA,
                            rawB,
                            max_skip=self.maxSkip,
                            pt_thresh=pt_thresh,
                        )
                    for pA, pB, err in pairs:
                        used_pts_A.add(pA.id)
                        used_pts_B.add(pB.id)
                        matched_pairs.append((pA.id, pB.id, err, "subbranch_recovery"))
                        added_any = True
                if not added_any:
                    break

        if _check_cancelled():
            return _empty_result()

        remap = {idB: idA for idA, idB, _, _ in matched_pairs if idA != idB}
        added_B = [p.id for p in ptsB if p.id not in used_pts_B]
        removed_A = [p.id for p in ptsA if p.id not in used_pts_A]
        elapsed_ms = (time.perf_counter() - t_start) * 1000.0

        return HeuristicAlignmentResult(
            remap=remap,
            matched_pairs=matched_pairs,
            matched_branch_points=matched_bp_records,
            unmatched_bps_A=unmatched_bps_A,
            unmatched_bps_B=unmatched_bps_B,
            paired_segments=n_paired_segments,
            added_points_B=added_B,
            removed_points_A=removed_A,
            effective_bp_thresh_um=bp_thresh,
            effective_point_thresh_um=pt_thresh,
            elapsed_ms=elapsed_ms,
        )

    def performAlignment(self, updateFunc: Optional[Callable[[], Optional[bool]]] = None) -> Dict[str, str]:
        """Drop-in signature compatible with `pydynamo_brain.model.IdAligner.performAlignment`."""
        return self.performAlignmentDetailed(updateFunc=updateFunc).remap


def sync_target_branches_to_reference(
    state: FullState,
    ref_tree: Tree,
    target_tree: Tree,
) -> None:
    """Sync `target_tree` primary branch continuations and branch IDs to `ref_tree`
    without mutating `ref_tree` (safe for multi-timepoint `t0 -> t1 -> t2` chains).
    """
    target_tree.cleanEmptyBranches()

    # 1. At matched bifurcations in target_tree, promote any child branch whose first
    #    matched point continues ref_tree's parent branch.
    for pt in list(target_tree.flattenPoints()):
        if pt.isRoot() or len(pt.children) == 0:
            continue
        ref_pt = ref_tree.getPointByID(pt.id)
        if ref_pt is None or ref_pt.parentBranch is None:
            continue
        ref_branch_id = ref_pt.parentBranch.id
        cur_nxt = pt.nextPointInBranch(1, noWrap=True)
        if cur_nxt is not None:
            ref_cur_nxt = ref_tree.getPointByID(cur_nxt.id)
            if (
                ref_cur_nxt is not None
                and ref_cur_nxt.parentBranch is not None
                and ref_cur_nxt.parentBranch.id == ref_branch_id
            ):
                continue
        for ch in list(pt.children):
            if not ch.points:
                continue
            for cand_pt in ch.points[:3]:
                ref_cand = ref_tree.getPointByID(cand_pt.id)
                if (
                    ref_cand is not None
                    and ref_cand.parentBranch is not None
                    and ref_cand.parentBranch.id == ref_branch_id
                ):
                    target_tree.continueParentBranchIfFirst(ch.points[0])
                    break
            else:
                continue
            break

    target_tree.cleanEmptyBranches()

    # 2. Match branch IDs in target_tree to corresponding branches in ref_tree,
    #    falling back to first-point ID for newly added branches.
    claimed_ref_branches: Set[str] = set()
    unassigned_branches = []

    # Pass 2a: exact branch-origin match (same parentPoint ID)
    for branch in target_tree.branches:
        if not branch.points:
            continue
        matched_branch_id: Optional[str] = None
        for p in branch.points[:3]:
            ref_p = ref_tree.getPointByID(p.id)
            if (
                ref_p is not None
                and ref_p.parentBranch is not None
                and ref_p.parentBranch.id not in claimed_ref_branches
                and branch.parentPoint is not None
                and ref_p.parentBranch.parentPoint is not None
                and branch.parentPoint.id == ref_p.parentBranch.parentPoint.id
            ):
                matched_branch_id = ref_p.parentBranch.id
                break
        if matched_branch_id is not None:
            claimed_ref_branches.add(matched_branch_id)
            state.setBranchIDWithoutCollision(target_tree, branch, matched_branch_id)
        else:
            unassigned_branches.append(branch)

    # Pass 2b: fallback to unclaimed ref branch of first point, else first-point ID
    for branch in unassigned_branches:
        p0 = branch.points[0]
        ref_p0 = ref_tree.getPointByID(p0.id)
        if (
            ref_p0 is not None
            and ref_p0.parentBranch is not None
            and ref_p0.parentBranch.id not in claimed_ref_branches
        ):
            claimed_ref_branches.add(ref_p0.parentBranch.id)
            state.setBranchIDWithoutCollision(target_tree, branch, ref_p0.parentBranch.id)
        else:
            state.setBranchIDWithoutCollision(target_tree, branch, p0.id)


def apply_heuristic_id_alignment(
    state: FullState,
    remap: Dict[str, str],
    ref_idx: int = 0,
    target_idx: int = 1,
    sort_branches_minimal_angle: bool = True,
    unmatched_target_ids: Optional[Sequence[str]] = None,
) -> None:
    """Apply collision-safe ID remapping (and optional minimal-angle canonicalization) in-place."""
    ref_tree = state.trees[ref_idx]
    target_tree = state.trees[target_idx]

    if sort_branches_minimal_angle:
        sort_tree_branches_minimal_angle(ref_tree)
        sort_tree_branches_minimal_angle(target_tree)

    cached_pts = {old_id: target_tree.getPointByID(old_id) for old_id in remap}
    unmatched_pts = (
        [target_tree.getPointByID(uid) for uid in unmatched_target_ids]
        if unmatched_target_ids is not None
        else []
    )

    for old_id, new_id in remap.items():
        pt = cached_pts.get(old_id)
        if pt is not None:
            state.setPointIDWithoutCollision(target_tree, pt, new_id)

    if unmatched_pts:
        ref_ids = {p.id for p in ref_tree.flattenPoints()}
        for pt in unmatched_pts:
            if pt is not None and pt.id in ref_ids:
                pt.id = state.nextPointID()

    if sort_branches_minimal_angle:
        ref_tree.cleanBranchIDs()
        target_tree.cleanBranchIDs()
    else:
        sync_target_branches_to_reference(state, ref_tree, target_tree)
