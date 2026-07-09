import numpy as np
import random
import copy
import math

from sklearn.cluster import DBSCAN
from sklearn.neighbors import NearestNeighbors

from skimage.measure import label, regionprops
from skimage.morphology import skeletonize_3d, dilation, erosion, remove_small_objects
from skimage.segmentation import expand_labels
from skimage.filters import gaussian, roberts
from skimage import feature

from scipy.stats import mode
from scipy.ndimage import zoom
from scipy import ndimage

from scipy.ndimage import center_of_mass, convolve
from scipy.spatial import cKDTree

import pydynamo_brain.util as util

from pydynamo_brain.model import *
from pydynamo_brain.ui.branchToColorMap import BranchToColorMap
from pydynamo_brain.util.util import douglasPeucker
from pydynamo_brain.util import imageCache
from pydynamo_brain.util import sortedBranchIDList
from .inference import modelPredict

_IMG_CACHE = util.ImageCache()


# Module-level: 26-connectivity neighbor offsets sorted face -> edge -> corner.
# Used by the topological skeleton walk that replaces orderPointList.
_NEIGHBOR_OFFSETS_26 = sorted(
    [(dz, dy, dx)
     for dz in (-1, 0, 1)
     for dy in (-1, 0, 1)
     for dx in (-1, 0, 1)
     if not (dz == 0 and dy == 0 and dx == 0)],
    key=lambda o: abs(o[0]) + abs(o[1]) + abs(o[2]),
)


def _walk_fragment(coord_set, start):
    """Walk a 1-voxel-thick fragment from `start` along 26-connected
    neighbors, preferring face-adjacent neighbors. O(N) replacement for
    OG's orderPointList (which was O(N^2)). Returns list of (z,y,x) tuples.
    """
    ordered = [start]
    visited = {start}
    cur = start
    while True:
        nxt = None
        for dz, dy, dx in _NEIGHBOR_OFFSETS_26:
            cand = (cur[0] + dz, cur[1] + dy, cur[2] + dx)
            if cand in coord_set and cand not in visited:
                nxt = cand
                break
        if nxt is None:
            break
        visited.add(nxt)
        ordered.append(nxt)
        cur = nxt
    return ordered


class TectalTracingFromSoma():

    def __init__(self, parentActions, fullState, history):
        self.parentActions = parentActions
        self.state = fullState
        self.history = history
        self.branchToColorMap = BranchToColorMap()
        self.epislon_val = 1.25
        self.xyzScale = self.state.projectOptions.pixelSizes
        self.threshold = 10
        self.training_set_xy = 0.230
        self.scale_ratio = 1


    def segmentedSkeleton(self, img2skel):
        # Takes an skeletonized image and segments the skeleton per plane
        # Returns segments as unique values in 3D array
        skel = skeletonize_3d(img2skel)

        segsPerPlane = np.zeros(img2skel.shape)
        foreground, background = 1, 2

        for i in range(skel.shape[0]):

            edges = sobel(skel[i, :, :])
            plane = skel[i, :, :]

            seeds = np.zeros((512, 512))

            seeds[plane < .5] = background
            seeds[skel[i, :, :] > .5] = foreground
            ws = watershed(edges, seeds)
            segments = label(ws == foreground)
            temp_max = np.max(segsPerPlane)
            segments = segments + temp_max
            segments[segments == temp_max] = 0
            segsPerPlane[i, :, :] = segments

        return segsPerPlane, skel

    def findEndsAndJunctions(self, points, skelly_image):
        skelly_image[skelly_image > 0] = 1
        end_points = []
        y_points = []

        for point in range(points[0].shape[0]):
            i = points[0][point]
            j = points[1][point]
            window = skelly_image[i - 1:i + 2, j - 1:j + 2]

            if np.sum(window) <= 2:
                end_points.append((j, i))
            if np.sum(window) == 4:
                y_points.append((j, i))

            return end_points, y_points

    def _estimate_soma_radius_intensity(self, imgVolume, soma_point_zyx):
        """Estimate soma radius using the radiusFromIntensity root-point method.
        
        Returns radius in working-frame xy pixels.
        """

        
        z, y, x = soma_point_zyx
        plane = imgVolume[z, :, :]
        
        # Edge map weighted by Canny edges
        modifiedPlane = roberts(plane)
        modifiedPlane = ndimage.gaussian_filter(modifiedPlane, sigma=3)
        edges = feature.canny(plane, sigma=2).astype(float)
        edges[edges == 0] = np.nan
        modifiedPlane = edges * modifiedPlane
        
        # Distance transform from the soma point
        plane01 = np.ones(plane.shape)
        plane01[round(y), round(x)] = 0
        planeDist = ndimage.distance_transform_edt(plane01)
        
        # Sweep disk radii; find radius where edge-energy is maximized
        X_POINTS = 100
        SQUISH = 1
        MAX_DIST_PX = int(60 * self.scale_ratio)  # resolution-aware
        xs = 1 + np.power(np.arange(0, 1, 1 / X_POINTS), SQUISH) * (MAX_DIST_PX - 1)
        
        ys = []
        for r in xs:
            selected = (planeDist < r)
            # nanmean since modifiedPlane has NaNs where Canny was 0
            ys.append(np.nanmean(modifiedPlane[selected]))
        
        ys = np.array(ys)
        if np.all(np.isnan(ys)):
            return 15.0 * self.scale_ratio  # fallback
        
        radius_px = xs[int(np.nanargmax(ys))]
        print(f"Soma radius (intensity method): {radius_px:.1f} px (working frame)")
        return float(radius_px)

    def _returnBranchPoints(self, skelFragment, skellID=1,):
        factor = self.epislon_val
        points = np.where(skelFragment == skellID)
        points = np.array(points)
        points = [[_i[0], _i[1]] for _i in zip(points[0, :], points[1, :])]
        allPointTree = KDTree(points)
        sortedAllPoints = np.zeros_like(points)

        for i, c in enumerate(allPointTree.query(np.array(points[0]).reshape(1, -1), k=len(points))[1][0]):
            sortedAllPoints[i, :] = points[c]

        reducedpoints = douglasPeucker(sortedAllPoints, factor)

        pointArray = np.array(reducedpoints)
        sortedPoints = np.zeros_like(pointArray)
        kdTree = KDTree(pointArray)
        for i, c in enumerate(kdTree.query(np.array([0, 0]).reshape(1, -1), k=pointArray.shape[0])[1][0]):

            sortedPoints[i, :] = pointArray[c, :]

        return sortedPoints

    def find_skeleton_3Dpoints(self, skelly_image):
        """Vectorized: convolve binary skeleton with 3x3x3 ones kernel
        for neighbor counts, then threshold. Same result as OG's
        Python-loop window slicing, ~100x faster.

        Endpoint: <=2 (self + <=1 neighbor)
        Junction: >=4 (self + >=3 neighbors)
        """
        skelly_image[skelly_image > 0] = 1
        skel_bin = skelly_image.astype(np.uint8)
        kernel = np.ones((3, 3, 3), dtype=np.uint8)
        counts = convolve(skel_bin, kernel, mode='constant', cval=0)
        counts = counts * skel_bin

        end_mask = (skel_bin == 1) & (counts <= 2)
        junc_mask = (skel_bin == 1) & (counts >= 4)

        end_points = [tuple(p) for p in np.argwhere(end_mask)]
        y_points = [tuple(p) for p in np.argwhere(junc_mask)]
        return end_points, y_points

    def DouglasPeucker3D(self, PointList, epsilon):
        """Iterative, vectorized Ramer-Douglas-Peucker in 3D.

        Same result as OG's recursive version, but inner distance
        computation is vectorized and recursion is unrolled to a stack.
        """
        if not PointList:
            return []
        if len(PointList) < 3:
            return [tuple(p) for p in PointList]
        pts = np.asarray(PointList, dtype=np.float64)
        n = len(pts)
        keep = np.zeros(n, dtype=bool)
        keep[0] = keep[-1] = True
        stack = [(0, n - 1)]
        while stack:
            i, j = stack.pop()
            if j - i < 2:
                continue
            seg = pts[j] - pts[i]
            seg_len = np.linalg.norm(seg)
            between = pts[i + 1:j] - pts[i]
            if seg_len == 0:
                d = np.linalg.norm(between, axis=1)
            else:
                d = np.linalg.norm(np.cross(seg, between), axis=1) / seg_len
            k = int(np.argmax(d))
            if d[k] > epsilon:
                idx = i + 1 + k
                keep[idx] = True
                stack.append((i, idx))
                stack.append((idx, j))
        return [tuple(p) for p in pts[keep]]

    def generateTree(self, treeRoot, somaCenter, skel, soma_radius):

        # Support Functions
        def distance_3d(point1, point2):
            return math.sqrt((point1[0] - point2[0])**2 + (point1[1] - point2[1])**2 + (point1[2] - point2[2])**2)

        def returnBranchingNode(list_of_points, list_of_branch_nodes, junction=None):
            _points = copy.deepcopy(list_of_points)

            junction_point_array = np.array(list_of_branch_nodes)
            branch_array = np.array(_points[-1])
            # cKDTree instead of brute-force NearestNeighbors
            k = min(3, len(junction_point_array))
            _tree = cKDTree(junction_point_array)
            distances, indices = _tree.query(branch_array, k=k)
            indices = np.atleast_1d(indices)

            if junction is None:
                return tuple(junction_point_array[indices[0]])
            else:
                closest_branch_points = tuple(junction_point_array[indices[0]])
                if junction == closest_branch_points and len(indices) >= 2:
                    return tuple(junction_point_array[indices[1]])
                return closest_branch_points

        def closestBranchingNode(list_of_points, list_of_branch_nodes):
            junction_point_array = np.array(list_of_branch_nodes)
            branch_array = np.array(list_of_points)
            _tree = cKDTree(junction_point_array)
            distances, indices = _tree.query(branch_array, k=1)
            if np.atleast_1d(distances)[0] > 10:
                return None
            idx = np.atleast_1d(indices)[0]
            return tuple(junction_point_array[idx])

        # Replaces OG's brute-force sklearn NN — same answer, much faster
        def returnClosetTreePoint(treeKdtree, treepoints, point):
            distance, index = treeKdtree.query(np.asarray(point), k=1)
            return tuple(treepoints[int(index)])

        skel[somaCenter[0], somaCenter[1], somaCenter[2]] = 0
        # Find all of the branch nodes and ends in the dendrites
        end_points, y_points = self.find_skeleton_3Dpoints(skel)

        # Use DBSCAN to cluster nearby branch nodes (within 10 pixels) — same as OG
        epsilon = 10 
        min_samples = 2
        points = np.array(y_points)

        clustering = DBSCAN(eps=epsilon, min_samples=min_samples).fit(points)

        cluster_ids = clustering.labels_
        _cleanBranchNodes = []
        for cluster_id in np.unique(cluster_ids):
            if cluster_id == -1:
                noise_points = points[cluster_ids == cluster_id]
                _cleanBranchNodes.extend(noise_points)
            else:
                cluster_members = points[cluster_ids == cluster_id]
                centroid = np.mean(cluster_members, axis=0)
                _cleanBranchNodes.append(centroid)

        # Use the branch nodes to break up the skeleton into branches
        for _branchNode in y_points:
            skel[_branchNode[0], _branchNode[1], _branchNode[2]] = 0
        line_fragments = label(skel)

        # Use soma point cloud to find end points of primary and basal dendrites
        end_pointArray = np.array(end_points)

        # cKDTree instead of brute-force NN
        _endKdtree = cKDTree(end_pointArray)
        somaDists, somaIndex = _endKdtree.query(np.asarray(somaCenter), k=2)
        somaIndex = np.atleast_1d(somaIndex)

        _closeBranchEnds = np.unique(end_pointArray[somaIndex], axis=0)
        somaEndPoints = np.unique(_closeBranchEnds, axis=0)
        # OG quirk: somaEndPoints[0] is the first row (a single point). Preserved.
        somaEnds = [tuple(somaEndPoints[0])]

        endNodeSet = set(end_points)
        somaEndSet = set(somaEnds)

        # Take all endpoints within some radius of the soma, not just the closest
        R_primary = soma_radius + (25 * self.scale_ratio)  # pixels in working frame
        soma_neighbor_idx = _endKdtree.query_ball_point(np.asarray(somaCenter), R_primary)
        somaEnds = list({tuple(end_pointArray[i]) for i in soma_neighbor_idx})
        if not somaEnds:
            # fall back to OG behaviour
            _, idx = _endKdtree.query(np.asarray(somaCenter), k=1)
            somaEnds = [tuple(end_pointArray[int(np.atleast_1d(idx)[0])])]
        # Get the points of each branch and order them based on distance from
        # an end or branching node. OG's orderPointList was O(N^2) — replaced
        # with O(N) topological walk along skeleton voxels (same ordering).
        _branchIds = np.unique(line_fragments)
        orderedBranches = []

        # Pre-bin voxel coords by fragment id so we don't np.where per id
        frag_coords = {}
        nz = np.argwhere(line_fragments > 0)
        if len(nz) > 0:
            ids = line_fragments[nz[:, 0], nz[:, 1], nz[:, 2]]
            for vid in np.unique(ids):
                mask = ids == vid
                frag_coords[int(vid)] = {tuple(p) for p in nz[mask]}

        _cleanBranchNodes_arr = np.array(_cleanBranchNodes)

        for _id in _branchIds:
            if _id > 0:
                coord_set = frag_coords.get(int(_id))
                if coord_set is None or len(coord_set) <= 2:
                    continue

                _pointSet = coord_set
                # Find the intersection
                shared_points = endNodeSet.intersection(_pointSet)

                if shared_points:
                    # OG: order points starting from any endpoint in the fragment
                    _endNode = list(shared_points)[0]
                    branchPoints = _walk_fragment(coord_set, _endNode)
                    orderedBranches.append(branchPoints)
                else:
                    # OG: start from the voxel in the fragment closest to a junction
                    coords_arr = np.array(list(coord_set))
                    _tree = cKDTree(coords_arr)
                    dist, indices = _tree.query(_cleanBranchNodes_arr, k=1)
                    min_idx = int(np.argmin(dist))
                    _firstPoint = tuple(coords_arr[indices[min_idx]])
                    branchPoints = _walk_fragment(coord_set, _firstPoint)
                    orderedBranches.append(branchPoints)

        # Find primary and basal dendrites and connect them
        _orderedBranches = copy.deepcopy(orderedBranches)
        TreeBranches = []
        junctionsInTree = []
        endNum = set(end_points)
        somaEndSet = set(somaEnds)
        for path in _orderedBranches:
            _treeBranch = []
            _points = path
            _pointSet = set(_points)
            shared_points = somaEndSet.intersection(_pointSet)

            if shared_points:
                _endNode = list(shared_points)[0]

                if (_endNode == _points[-1]):
                    _points.reverse()

                if (_endNode == _points[0]):
                    _points.insert(0, (treeRoot[0], treeRoot[1], treeRoot[2]))
                    _points.insert(1, (somaCenter[0], somaCenter[1], somaCenter[2]))
                    junction = returnBranchingNode(_points, _cleanBranchNodes)
                    junctionsInTree.append(junction)
                    _points.append(junction)
                    TreeBranches.append(_points)
                    _ = _orderedBranches.pop(_orderedBranches.index(_points))

                else:
                    # Soma-end was mid-path (rare): re-walk from it so it
                    # ends up at [0] without losing voxels.
                    _points = _walk_fragment(set(_points), _endNode)
                    _points.insert(0, (treeRoot[0], treeRoot[1], treeRoot[2]))
                    _points.insert(1, (somaCenter[0], somaCenter[1], somaCenter[2]))
                    junction = returnBranchingNode(_points, _cleanBranchNodes)
                    junctionsInTree.append(junction)
                    TreeBranches.append(_points)
                    _ = _orderedBranches.pop(_orderedBranches.index(path))

        # Tree Object to assemble
        newTree = Tree()
        newTree._parentState = self.state.uiStates[0]

        # List to hold points added to the tree
        _TreePoints = []

        _TreePoints.append(tuple([int(somaCenter[2]), int(somaCenter[1]), int(somaCenter[0])]))
        rootNode = Point(id='root',
                         location=tuple([int(treeRoot[2]), int(treeRoot[1]), int(treeRoot[0])]))
        newTree.rootPoint = rootNode
        print('Root Node:', rootNode.location)
        newTree.rootPoint.parentBranch = None

        # Maintain a parallel coord -> Point object map so we don't have to
        # call newTree.closestPointTo (which scans the whole tree) on every
        # branch attach. Index into both arrays with the same kdtree result.
        _treePointObjs = [rootNode]

        # Replace with normal branchID and PointID in the future
        _branchNum = 0
        _pointNum = 1

        # Add basal and primary dendrite
        for _path in TreeBranches:
            _path = self.DouglasPeucker3D(_path, self.epislon_val)
            # The first point of the path is treeRoot (in zyx). Parent is root.
            _parentNode = rootNode
            _ = _path.pop(0)
            newBranch = Branch(id='b' + str(_branchNum))
            _branchNum += 1
            for xyz in _path:
                _TreePoints.append(xyz)
                nextPoint = Point(
                    id='p' + str(_pointNum),
                    location=tuple([int(xyz[2]), int(xyz[1]), int(xyz[0])])
                )

                _pointNum += 1
                newBranch.addPoint(nextPoint)
                _treePointObjs.append(nextPoint)

            newBranch.setParentPoint(_parentNode)
            newTree.addBranch(newBranch)

        # Initialize cKDTree for points in tree (replaces brute-force NN)
        _treePointArr = np.array(_TreePoints)
        _nbrsTree = cKDTree(_treePointArr)

        # CloestPointTo is super slow — replaced via the parallel-array
        # lookup above. Rebuild once per outer pass instead of per branch.
        remainingBranches = -1
        failures = 0
        while failures < 25:
            _treePointArr = np.array(_TreePoints)
            _nbrsTree = cKDTree(_treePointArr)
            attached_this_pass = []
            for _path in _orderedBranches:

                _pointSet = set(_path)
                _points = _path
                shared_points = endNum.intersection(_pointSet)
                if shared_points:
                    _endNode = list(shared_points)[0]
                    if (_endNode == _points[0]):
                        _points.reverse()
                    if (_endNode == _points[-1]):
                        # Dynamo points are xyz, image points are zxy
                        _, idx0 = _nbrsTree.query(np.asarray(_points[0]), k=1)
                        idx0 = int(idx0)
                        _closestTreeNode = tuple(_treePointArr[idx0])
                        if distance_3d(_closestTreeNode, _points[0]) < 10  * self.scale_ratio:

                            _parentNode = _treePointObjs[idx0]
                            _p_points = self.DouglasPeucker3D(_points, self.epislon_val)

                            newBranch = Branch(id='b' + str(_branchNum))
                            _branchNum += 1
                            for xyz in _points:
                                _TreePoints.append(xyz)

                                nextPoint = Point(
                                    id='p' + str(_pointNum),
                                    location=tuple([int(xyz[2]), int(xyz[1]), int(xyz[0])])
                                )

                                _pointNum += 1
                                newBranch.addPoint(nextPoint)
                                _treePointObjs.append(nextPoint)
                            newBranch.setParentPoint(_parentNode)
                            newTree.addBranch(newBranch)
                            attached_this_pass.append(_path)
                            remainingBranches = len(_orderedBranches) - len(attached_this_pass)
                else:
                    _, idx0 = _nbrsTree.query(np.asarray(_points[0]), k=1)
                    idx0 = int(idx0)
                    _closestTreeNode = tuple(_treePointArr[idx0])
                    if distance_3d(_closestTreeNode, _points[0]) > 10  * self.scale_ratio:
                        _, idx1 = _nbrsTree.query(np.asarray(_points[-1]), k=1)
                        idx1 = int(idx1)
                        _closestTreeNode = tuple(_treePointArr[idx1])
                        idx0 = idx1  # so _parentNode lookup uses the right index
                    if distance_3d(_closestTreeNode, _points[-1]) < 10  * self.scale_ratio:
                        _points.reverse()
                    if distance_3d(_closestTreeNode, _points[0]) < 10  * self.scale_ratio:
                        _points = self.DouglasPeucker3D(_points, self.epislon_val)

                        _parentNode = _treePointObjs[idx0]

                        newBranch = Branch(id='b' + str(_branchNum))
                        _branchNum += 1
                        for xyz in _points:
                            _TreePoints.append(xyz)
                            nextPoint = Point(
                                id='p' + str(_pointNum),
                                location=tuple([int(xyz[2]), int(xyz[1]), int(xyz[0])])
                            )

                            _pointNum += 1
                            newBranch.addPoint(nextPoint)
                            _treePointObjs.append(nextPoint)
                        newBranch.setParentPoint(_parentNode)
                        newTree.addBranch(newBranch)
                        attached_this_pass.append(_path)
                        remainingBranches = len(_orderedBranches) - len(attached_this_pass)

            # Remove all attached paths after the pass (OG popped per-iteration
            # but that's not safe while iterating — defer to here).
            for _p in attached_this_pass:
                if _p in _orderedBranches:
                    _orderedBranches.remove(_p)

            if len(_orderedBranches) == remainingBranches:
                failures += 1

        newTree.updateAllPrimaryBranches()
        print("Branches in tree:", len(newTree.branches))
        for branch in newTree.branches:
            if branch.worldLengths()[0] < 5:
                print("True")
                if branch.hasChildren() == False:
                    reverseIndex = list(reversed(range(len(branch.points))))
                    for i in reverseIndex:
                        newTree.removePointByID(branch.points[i].id)
        newTree.updateAllPrimaryBranches()
        print("Branches in tree:", len(newTree.branches))
        return newTree

    def dendriteTracingFromSoma(self):
        if self.state.trees[0].rootPoint is None:
            print("Must place root node")
            return
        if len(self.state.trees[0].flattenPoints()) > 1:
            print("Tree reconstuction already started")
            return
        # TODO Pull in image from imageChache
        volume = _IMG_CACHE.getVolume(self.state.uiStates[0].imagePath)

        # Work with the current channel
        imgVolume = volume[self.state.channel, :, :, :]
        volume = _IMG_CACHE.getVolume(self.state.uiStates[0].imagePath)

        scaled = False
        xy_pixel_size = self.state.projectOptions.pixelSizes[1]
        scale_ratio = xy_pixel_size / self.training_set_xy
        print(xy_pixel_size, self.training_set_xy)
        if not (0.8 <= scale_ratio <= 1.2):
            print('Scaling input image')
            imgVolume = zoom(imgVolume, (1, scale_ratio, scale_ratio))
            scaled = True
            self.scale_ratio = scale_ratio
        


        # Vectorized post-process: percentile and max per (channel, z) plane
        # in one shot instead of the OG triple Python loop.
        def _postProcess(image):
            image = image.astype(np.float32) ** 0.95  # Gamma correction
            mn = np.percentile(image, 10, axis=(-2, -1), keepdims=True)
            mx = image.max(axis=(-2, -1), keepdims=True)
            image = 255.0 * (image - mn) / (mx - mn + 1e-8)
            return np.round(image.clip(0, 255)).astype(np.uint8)

        imgVolume = _postProcess(imgVolume)
        
        

        
        # IMAGE [z, x , y]
        pixelClasses, other = modelPredict(imgVolume, "Soma+Dendrite")


        somaCoords = self.state.trees[0].rootPoint.location
        print('somaCoords', somaCoords)
        print('scale_ratio', scale_ratio)

        #SOMA_POINT = [int(somaCoords[2]), int(somaCoords[1]), int(somaCoords[0])]

        # User-placed root is in original-frame xyz. Convert to scaled-frame zyx.
        if scaled:
            SOMA_POINT = [
                int(somaCoords[2]),                       # z unchanged
                int(somaCoords[1] * scale_ratio),         # x scaled
                int(somaCoords[0] * scale_ratio),         # y scaled
            ]
        else:
            SOMA_POINT = [int(somaCoords[2]), int(somaCoords[1]), int(somaCoords[0])]
        print('SOMA POINT', SOMA_POINT)
        soma_radius = self._estimate_soma_radius_intensity(imgVolume, SOMA_POINT)
        neuron = pixelClasses[:, :, :].copy()
        neuron[neuron == 3] = 0

        neuron = gaussian(neuron, .5)
        neuron[neuron != 0] = 1

        neuron[neuron != 0] = 1

        neuron = neuron.astype(bool)
        neuron = remove_small_objects(neuron, 500)

        neuron = neuron.astype(np.float16)
        neuron = gaussian(neuron, .8)
        neuron = neuron / np.max(neuron)

        # Speedup: crop to neuron bbox before skeletonizing. The skel is
        # only nonzero where the mask is, so working in a tight crop is
        # 3-5x faster on big volumes. Re-embed at the end.
        # NB: gaussian smearing extends the support slightly; pad to keep it.
        if not neuron.any():
            print("No neuron mask found")
            return None
        nzc = np.argwhere(neuron > 0.5)
        zmin, ymin, xmin = nzc.min(axis=0)
        zmax, ymax, xmax = nzc.max(axis=0) + 1
        pad = 5
        zmin = max(0, zmin - pad)
        ymin = max(0, ymin - pad)
        xmin = max(0, xmin - pad)
        zmax = min(neuron.shape[0], zmax + pad)
        ymax = min(neuron.shape[1], ymax + pad)
        xmax = min(neuron.shape[2], xmax + pad)

        neuron_crop = neuron[zmin:zmax, ymin:ymax, xmin:xmax]
        skel_crop = skeletonize_3d(neuron_crop)

        skel_crop[skel_crop > 0] = 1
        skel_crop = skel_crop.astype(bool)
        skel_crop = remove_small_objects(skel_crop, 75, connectivity=3)

        # Largest-component selection using bincount (faster than regionprops
        # when we only need the largest area).
        labeled = label(skel_crop.astype(int))
        if labeled.max() == 0:
            print("No skeleton found")
            return None
        areas = np.bincount(labeled.ravel())
        areas[0] = 0
        largest_label = int(np.argmax(areas))
        skel_crop = (labeled == largest_label).astype(bool)
        skel_crop = remove_small_objects(skel_crop, 300, connectivity=3)
        skel_crop = skel_crop.astype(int)

        # Embed back into full-size volume
        skel = np.zeros(neuron.shape, dtype=int)
        skel[zmin:zmax, ymin:ymax, xmin:xmax] = skel_crop

        skeletonPoints = np.array(np.where(skel == np.max(skel)))
        # cKDTree instead of brute-force NN
        _allTree = cKDTree(skeletonPoints.T)
        _, somaIndex = _allTree.query(np.asarray(SOMA_POINT), k=1)

        RootNode = skeletonPoints.T[int(somaIndex)]
        print(SOMA_POINT, RootNode)
        _autoTree = self.generateTree(SOMA_POINT, RootNode, skel.copy(), soma_radius)
        if scaled:
            inverse_scale = 1.0 / scale_ratio
            for branch in _autoTree.branches:
                    for point in branch.points:
                        if not point.isRoot():
                            x, y, z = point.location
                            point.location = (x * inverse_scale, y * inverse_scale, z)
                            # Scale radius too if your Point has it
                            if hasattr(point, 'radius') and point.radius is not None:
                                point.radius *= inverse_scale
            x, y, z = _autoTree.rootPoint.location 
            _autoTree.rootPoint.location = (x * inverse_scale, y * inverse_scale, z)
        return _autoTree


def distance(p1, p2):
    d = math.sqrt(math.pow(p1[0] - p2[0], 2) +
                  math.pow(p1[1] - p2[1], 2) +
                  math.pow(p1[2] - p2[2], 2))
    return d