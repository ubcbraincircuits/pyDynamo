import numpy as np
import random
import copy
import math

from sklearn.cluster import DBSCAN
from sklearn.neighbors import NearestNeighbors

from skimage.measure import label, regionprops

from skimage.morphology import skeletonize_3d, dilation, erosion, remove_small_objects
from skimage.segmentation import expand_labels
from skimage.filters import gaussian

from scipy.ndimage import center_of_mass
from scipy.spatial import cKDTree

import pydynamo_brain.util as util

from pydynamo_brain.model import *
from pydynamo_brain.ui.branchToColorMap import BranchToColorMap
from pydynamo_brain.util.util import douglasPeucker
from pydynamo_brain.util import imageCache
from pydynamo_brain.util import sortedBranchIDList
from .biocytinModel import returnBiocytin
from tqdm import tqdm 
from tifffile import imread

from joblib import Parallel, delayed


_IMG_CACHE = util.ImageCache()

class BiocytinTracingFromSoma():

    def __init__(self, parentActions, fullState, history):
        self.parentActions = parentActions
        self.state = fullState
        self.history = history
        self.branchToColorMap = BranchToColorMap()
        self.epislon_val = 1
        self.xyzScale =  self.state.projectOptions.pixelSizes
        self.threshold = 10

  
    def find_skeleton_3Dpoints(self, skelly_image):
        # Force binary image
        skelly_image[skelly_image>0]=1

        points = np.where(skelly_image==1)
        end_points = []
        y_points = []

        for point in range(points[0].shape[0]):
            z = points[0][point]
            x = points[1][point]
            y = points[2][point]

            window=skelly_image[z-1:z+2, x-1:x+2, y-1:y+2]
            if np.sum(window)<=2:
                end_points.append((z,x,y))
            if np.sum(window)>=4:
                y_points.append((z,x,y))
        return end_points, y_points

    def DouglasPeucker3D(self, PointList, epsilon):
        """Returns reduced points list using the Ramer–Douglas–Peucker algorithm in 3D

        Inputs:
        PointList: list of (z, x, y) tuples
        epsilon: threshold distance
        """
        if not PointList:
            return []

        # Convert list of tuples to numpy array for easier manipulation
        pointArray = np.array(PointList)
        dmax = 0
        index = 0
        end = pointArray.shape[0]

        p1 = pointArray[0]
        p2 = pointArray[-1]

        for i in range(1, end-1):
            p3 = pointArray[i]
            # Use np.linalg.norm to calculate the perpendicular distance in 3D
            d = np.linalg.norm(np.cross(p2-p1, p3-p1)) / np.linalg.norm(p2-p1)
            if d > dmax:
                index = i
                dmax = d

        results = []

        if dmax > epsilon:
            # Convert numpy arrays back to lists of tuples for recursive calls
            recResults1 = self.DouglasPeucker3D([tuple(pt) for pt in pointArray[:index+1]], epsilon)
            recResults2 = self.DouglasPeucker3D([tuple(pt) for pt in pointArray[index:]], epsilon)
            
            # Combine results from recursive calls, avoiding duplicate points
            results = recResults1[:-1] + recResults2
        else:
            results = [tuple(p1), tuple(p2)]

        return results

    def generateTree(self, treeRoot, somaCenter, skel):

        # Support Functions
        def distance_3d(point1, point2):
            return math.sqrt((point1[0] - point2[0])**2 + (point1[1] - point2[1])**2 + (point1[2] - point2[2])**2)

        def find_closest_point(reference_point, points):
            """Find the closest point to the reference point."""
            min_distance = float('inf')
            closest_point = None
            for point in points:
                dist = distance_3d(reference_point, point)
                if dist < min_distance:
                    min_distance = dist
                    closest_point = point
            return closest_point

        def orderPointList(reference_point, points):
            ordered_points = []
            while points:
                closest_point = find_closest_point(reference_point, points)
                ordered_points.append(closest_point)
                points.remove(closest_point)
                reference_point = closest_point
            return ordered_points

        def returnBranchingNode(list_of_points, list_of_branch_nodes, junction=None):
            _points = copy.deepcopy(list_of_points)

            junction_point_array = np.array(list_of_branch_nodes)  
            branch_array = np.array(_points[-1])  
            _nbrs = NearestNeighbors(n_neighbors=3, algorithm='kd_tree').fit(junction_point_array)

            distances, indices = _nbrs.kneighbors(branch_array.reshape(1, -1))
            if junction == None:
                closest_branch_point_indices = indices[:, 0]
      
                closest_branch_points = tuple(junction_point_array[closest_branch_point_indices][0])
                return closest_branch_points
            else:
                closest_branch_point_indices = indices[:, 0]
                closest_branch_points = tuple(junction_point_array[closest_branch_point_indices][0])
                if junction == closest_branch_points:
                    closest_branch_point_indices = indices[:, 1]
                    closest_branch_points = tuple(junction_point_array[closest_branch_point_indices][0])
                    return closest_branch_points

                else:
                    return closest_branch_points

        def closestBranchingNode(list_of_points, list_of_branch_nodes):
            _points = copy.deepcopy(list_of_points)

            junction_point_array = np.array(list_of_branch_nodes)  
            branch_array = np.array(_points)  
            _nbrs = NearestNeighbors(n_neighbors=1, algorithm='kd_tree').fit(junction_point_array)

            distances, indices = _nbrs.kneighbors(branch_array)
            if distances[:, 0][0] > 10:
                return None
            closest_branch_point_indices = indices[:, 0]

            closest_branch_points = tuple(junction_point_array[closest_branch_point_indices][0])

            
            return closest_branch_points

       
        def returnClosetTreePoint(tree_kdtree, treepoints, point):
            pointArray = np.array(point)
            distance, index = tree_kdtree.query(pointArray, k=1)
            print("closest point:", distance)
            closestPoint = tuple(treepoints[index])
            return closestPoint



        skel[somaCenter[0], somaCenter[1], somaCenter[2]] = 0
        end_points, y_points = self.find_skeleton_3Dpoints(skel)


        # Use DBSCAN to cluster nearby branch nodes (within 10 pixels)
        min_samples = 2
        points = np.array(y_points)

        print('Start DBSCAN')
        print('Point array size:', points.shape)
        def grid_based_clustering(points, grid_size):
            # Quantize point coordinates to grid
            quantized_points = np.floor(points / grid_size).astype(int)

            # Create a mapping from grid coordinates to point indices
            grid_dict = {}
            for idx, qp in enumerate(quantized_points):
                key = tuple(qp)
                grid_dict.setdefault(key, []).append(idx)

            # Extract clusters
            clusters = []
            for indices in grid_dict.values():
                cluster_points = points[indices]
                centroid = np.mean(cluster_points, axis=0)
                clusters.append(centroid)

            return clusters

        points = np.array(y_points)
        _cleanBranchNodes = grid_based_clustering(points, grid_size=10)


        # Use the branch nodes to break up the skeleton into branches
        for _branchNode in y_points:
            skel[_branchNode[0], _branchNode[1], _branchNode[2]] = 0
        line_fragments = label(skel)
        

        # Use soma point cloud to find end points of primary and basal dendrites
        end_pointArray = np.array(end_points)

        _somaNbrs = NearestNeighbors(n_neighbors=2, algorithm='kd_tree').fit(end_pointArray)
        somaDists, somaIndex = _somaNbrs.kneighbors(somaCenter.reshape(1, -1))

        _closeBranchEnds = np.unique(end_pointArray[somaIndex[:, :]], axis=0)
        somaEndPoints = np.unique(_closeBranchEnds, axis=0)
        somaEnds = [tuple(_somaEnd) for _somaEnd in somaEndPoints[0]]

        endNodeSet = set(end_points)
        somaEndSet = set(somaEnds)
        _branchPoints = NearestNeighbors(n_neighbors=1, algorithm='kd_tree').fit(_cleanBranchNodes)
        

        def returnClosetTreePoint(tree_kdtree, treepoints, point):
            pointArray = np.array(point)
            distance, index = tree_kdtree.query(pointArray, k=1)
            closestPoint = tuple(treepoints[index])
            return closestPoint

        def extract_branch_path(skeleton, start_point):
            path = []
            visited = np.zeros_like(skeleton, dtype=bool)
            stack = [start_point]
            visited[start_point] = True

            while stack:
                current_point = stack.pop()
                path.append(current_point)
                z, x, y = current_point

                # Define neighbor offsets
                neighbor_offsets = [offset for offset in np.ndindex(3, 3, 3) if offset != (1, 1, 1)]
                for dz, dx, dy in neighbor_offsets:
                    nz, nx, ny = z + dz - 1, x + dx - 1, y + dy - 1
                    if (0 <= nz < skeleton.shape[0] and
                        0 <= nx < skeleton.shape[1] and
                        0 <= ny < skeleton.shape[2] and
                        skeleton[nz, nx, ny] and
                        not visited[nz, nx, ny]):
                        visited[nz, nx, ny] = True
                        stack.append((nz, nx, ny))
            return path
        def get_skeleton_neighbors(skeleton, point):
            z, x, y = point
            neighbors = []
            for dz in [-1, 0, 1]:
                for dx in [-1, 0, 1]:
                    for dy in [-1, 0, 1]:
                        if dz == dx == dy == 0:
                            continue
                        nz, nx, ny = z + dz, x + dx, y + dy
                        if (0 <= nz < skeleton.shape[0] and
                            0 <= nx < skeleton.shape[1] and
                            0 <= ny < skeleton.shape[2] and
                            skeleton[nz, nx, ny]):
                            neighbors.append((nz, nx, ny))
            return neighbors
        def chunked_douglas_peucker(points, epsilon, chunk_size=500):
            simplified_points = []
            if len(points) > chunk_size:
                for i in range(0, len(points), chunk_size):
                    chunk = points[i:i+chunk_size]
                    simplified_chunk = self.DouglasPeucker3D(chunk, self.epislon_val)
                    simplified_points.extend(simplified_chunk)
            else:
                simplified_points = self.DouglasPeucker3D(points, self.epislon_val)
            return simplified_points
        ##

        _branchArray = np.zeros_like(skel)
        print('Main Branches')
        _branchIds = np.unique(line_fragments)
        print(_branchIds)
        orderedBranches = []
        print("Brances to add: ", len(orderedBranches))

        end_points_array = np.array(end_points)
        skel_shape = skel.shape
        end_indices = np.ravel_multi_index((end_points_array[:,0], end_points_array[:,1], end_points_array[:,2]), skel_shape)

        def process_branch(_id):
            if _id <= 0:
                return None
            _coords = np.where(line_fragments == _id)
            branchPoints_array = np.column_stack(_coords)
            if branchPoints_array.shape[0] <= 2:
                return None

            branch_indices = np.ravel_multi_index(branchPoints_array.T, skel_shape)
            shared_indices = np.intersect1d(branch_indices, end_indices)

            current_branch_mask = (line_fragments == _id).astype(np.uint8)

            if shared_indices.size > 0:
                _endNode = np.unravel_index(shared_indices[0], skel_shape)
                branch_path = extract_branch_path(current_branch_mask, _endNode)
            else:
                nbrs = NearestNeighbors(n_neighbors=1, algorithm='kd_tree').fit(branchPoints_array)
                distances, indices = nbrs.kneighbors(_cleanBranchNodes)
                min_idx = np.argmin(distances)
                _firstPoint = tuple(branchPoints_array[indices[min_idx][0]])
                branch_path = extract_branch_path(current_branch_mask, _firstPoint)

            if len(branch_path) > 3:
                branch_path = chunked_douglas_peucker(branch_path, 2, 100)
            return branch_path
        orderedBranches = Parallel(n_jobs=-1)(
            delayed(process_branch)(_id) for _id in tqdm(_branchIds)
        )
        #for _id in tqdm(_branchIds):
        #    process_branch(_id)    

        orderedBranches = [branch for branch in orderedBranches if branch is not None]
        
        def distance_3d(point1, point2):
            return math.sqrt((point1[0] - point2[0])**2 + (point1[1] - point2[1])**2 + (point1[2] - point2[2])**2)

        def find_closest_point(reference_point, points):
            """Find the closest point to the reference point."""
            min_distance = float('inf')
            closest_point = None
            for point in points:
                dist = distance_3d(reference_point, point)
                if dist < min_distance:
                    min_distance = dist
                    closest_point = point
            return closest_point

        def orderPointList(reference_point, points):
            ordered_points = []
            while points:
                closest_point = find_closest_point(reference_point, points)
                ordered_points.append(closest_point)
                points.remove(closest_point)
                reference_point = closest_point
            return ordered_points

        def returnBranchingNode(list_of_points, list_of_branch_nodes, junction=None):
            _points = copy.deepcopy(list_of_points)

            junction_point_array = np.array(list_of_branch_nodes)  
            branch_array = np.array(_points[-1])  
            _nbrs = NearestNeighbors(n_neighbors=3, algorithm='kd_tree').fit(junction_point_array)

            distances, indices = _nbrs.kneighbors(branch_array.reshape(1, -1))
            if junction == None:
                closest_branch_point_indices = indices[:, 0]

                closest_branch_points = tuple(junction_point_array[closest_branch_point_indices][0])
                return closest_branch_points
            else:
                closest_branch_point_indices = indices[:, 0]
                closest_branch_points = tuple(junction_point_array[closest_branch_point_indices][0])
                if junction == closest_branch_points:
                    closest_branch_point_indices = indices[:, 1]
                    closest_branch_points = tuple(junction_point_array[closest_branch_point_indices][0])
                    return closest_branch_points

                else:
                    return closest_branch_points

        def closestBranchingNode(list_of_points, list_of_branch_nodes):
            _points = copy.deepcopy(list_of_points)

            junction_point_array = np.array(list_of_branch_nodes)  
            branch_array = np.array(_points)  
            _nbrs = NearestNeighbors(n_neighbors=1, algorithm='kd_tree').fit(junction_point_array)

            distances, indices = _nbrs.kneighbors(branch_array)
            if distances[:, 0][0] > 10:
                return None
            closest_branch_point_indices = indices[:, 0]

            closest_branch_points = tuple(junction_point_array[closest_branch_point_indices][0])

            
            return closest_branch_points
      
        print("Brances to add: ", len(orderedBranches))

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
                    _points =  orderPointList(_endNode, _points)
                    _points.insert(0, (treeRoot[0], treeRoot[1], treeRoot[2]))
                    _points.insert(1, (somaCenter[0], somaCenter[1], somaCenter[2]))
                    junction = returnBranchingNode(_points, _cleanBranchNodes)
                    junctionsInTree.append(junction)
                    TreeBranches.append(_points) 
                    _ =_orderedBranches.pop(_orderedBranches.index(path))

        # Tree Object to assemble 
        newTree = Tree()

        # List to hold points added to the tree
        _TreePoints = []

        _TreePoints.append(tuple([int(somaCenter[2]), int(somaCenter[1]), int(somaCenter[0])]))
        rootNode = Point(id='root', 
                        location=tuple([int(treeRoot[2]), int(treeRoot[1]), int(treeRoot[0])]))
        newTree.rootPoint = rootNode
        newTree.rootPoint.parentBranch = None 

        # Replace with normal branchID and PointID in the future 
        _branchNum = 0
        _pointNum =  1
        print("basal and primary dendrites")
        # Add basal and primary dendrite
        print("Brances to add: ", len(_orderedBranches))
        print("Brances to add: ", len(TreeBranches))
        for _path in TreeBranches:
            _parentNode = newTree.closestPointTo((int(_path[0][2]), int(_path[0][1]), int(_path[0][0])))
            _ = _path.pop(0)
            newBranch = Branch(id = 'b'+str(_branchNum))
            _branchNum += 1
            for xyz in _path:
                _TreePoints.append(xyz)
                nextPoint = Point(
                        id = 'p'+str(_pointNum),
                        location = tuple([int(xyz[2]), int(xyz[1]), int(xyz[0])])
                        )
                        
                _pointNum += 1 
                newBranch.addPoint(nextPoint)

            newBranch.setParentPoint(_parentNode)
            newTree.addBranch(newBranch)
        print(len(newTree.branches))
        # Initialize NearestNeighbors for points in tree
        _treePointArr = np.array(_TreePoints)
        #_nbrsTree = NearestNeighbors(n_neighbors=1, algorithm='kd_tree').fit(_treePointArr)
        _nbrsTree = cKDTree(_treePointArr)

        print('Final Part')
        # CloestPointTo is super slow! Replace with nearestneighbor algo? 
        remainingBranches = -1
        failures = 0


        # Build KD-Tree once before the loop
        _treePointArr = np.array(_TreePoints)
        tree_kdtree = cKDTree(_treePointArr)

        print("Remaining Branches:", len(_orderedBranches))
        _dist = 25
        while failures < 35:
            print("Tree Points:", len(_TreePoints))
            print("Dynamo Branches:", len(newTree.branches))
            #_treePointArr = np.array(_TreePoints)
            #_nbrsTree = NearestNeighbors(n_neighbors=1, algorithm='kd_tree').fit(_treePointArr)
            for _path in _orderedBranches:
                remainingBranches = len(_orderedBranches)
                
                _pointSet = set(_path)
                _points = _path
                shared_points = endNum.intersection(_pointSet)
                if shared_points:
                    _endNode = list(shared_points)[0]
                    if (_endNode == _points[0]):
                        _points.reverse()
                    if (_endNode == _points[-1]):
                        # Dynamo points are xyz, image points are zxy
                        _closestTreeNode = returnClosetTreePoint(_nbrsTree, _treePointArr, _points[0])
                        if distance_3d(_closestTreeNode, _points[0]) < _dist:
                            
                            
                            _parentNode = newTree.closestPointTo((int(_closestTreeNode[2]), int(_closestTreeNode[1]), int(_closestTreeNode[0])))
                            _p_pointsath = self.DouglasPeucker3D(_points, 1)

                            newBranch = Branch(id = 'b'+str(_branchNum))
                            _branchNum += 1
                            for xyz in _points:
                                _TreePoints.append(xyz)

                                nextPoint = Point(
                                        id = 'p'+str(_pointNum),
                                        location = tuple([int(xyz[2]), int(xyz[1]), int(xyz[0])])
                                        )

                                _pointNum += 1 
                                newBranch.addPoint(nextPoint)
                            newBranch.setParentPoint(_parentNode)
                            newTree.addBranch(newBranch)
                            _ = _orderedBranches.pop(_orderedBranches.index(_path))
                            remainingBranches = len(_orderedBranches)


                            #Only update when new branches are added
                            _treePointArr = np.array(_TreePoints)
                            tree_kdtree = cKDTree(_treePointArr)
                else:
                    _closestTreeNode = returnClosetTreePoint(tree_kdtree, _treePointArr, _points[0])
                    if distance_3d(_closestTreeNode, _points[0]) > _dist:
                        _closestTreeNode = returnClosetTreePoint(tree_kdtree, _treePointArr, _points[-1])  
                    if distance_3d(_closestTreeNode, _points[-1]) < _dist:
                            _points.reverse()
                    if distance_3d(_closestTreeNode, _points[0]) < _dist:
                        _points = self.DouglasPeucker3D(_points, 0)

                        _parentNode = newTree.closestPointTo((int(_closestTreeNode[2]), int(_closestTreeNode[1]), int(_closestTreeNode[0])))
                

                        newBranch = Branch(id = 'b'+str(_branchNum))
                        _branchNum += 1
                        for xyz in _points:
                            _TreePoints.append(xyz)
                            nextPoint = Point(
                                    id = 'p'+str(_pointNum),
                                    location = tuple([int(xyz[2]), int(xyz[1]), int(xyz[0])])
                                    )

                            _pointNum += 1 
                            newBranch.addPoint(nextPoint)
                        newBranch.setParentPoint(_parentNode)
                        newTree.addBranch(newBranch)
                        _ = _orderedBranches.pop(_orderedBranches.index(_path))
                        remainingBranches = len(_orderedBranches)
                        _treePointArr = np.array(_TreePoints)
                        tree_kdtree = cKDTree(_treePointArr)
                        if remainingBranches == 0:
                            break
            print(remainingBranches)        
            if len(_orderedBranches) == remainingBranches:
                print(failures)
                failures += 1
                _treePointArr = np.array(_TreePoints)
                tree_kdtree = cKDTree(_treePointArr)
            if failures >= 25:
                if _dist < 35:
                    _dist += 2
                    failures = 0
            if remainingBranches <= 0:
                failures = 25
                break

        return newTree
       
  
    def dendriteTracingFromSoma(self):
        if self.state.trees[0].rootPoint ==None:
            print("Must place root node")
            return
        if len(self.state.trees[0].flattenPoints()) > 1:
            print("Tree reconstuction already started")
            return
        # TODO Pull in image from imageChache
        imgVolume = imread(self.state.uiStates[0].imagePath)

        # Work with the current channel
        #imgVolume = volume[self.state.channel,:,:,:]

   
        # IMAGE [z, x , y]
        skel = returnBiocytin(imgVolume)

        somaCoords = self.state.trees[0].rootPoint.location
        SOMA_POINT = [int(somaCoords[2]), int(somaCoords[1]), int(somaCoords[0])]
        
        # Create a skeleton of the dendrites #spooky
        #skel = skeletonize_3d(neuron)

        #skel[skel > 0 ] = 1
        #skel = skel.astype(bool)
        #skel = remove_small_objects(skel, 300, connectivity=5)
        #skel = skel.astype(int)

        #regions = regionprops(skel)
        #largest_region = max(regions, key=lambda r: r.area)
        #largest_component = (skel == largest_region.label)

        #skel = (skel == largest_region.label)
        #skel = skel.astype(int)
        #skel = skeletonize_3d(neuron)
        print(SOMA_POINT)
        skeletonPoints = np.argwhere(skel)
        print('Find Soma Location in Tree')
        _allPoints = cKDTree(skeletonPoints)
        distance, index = _allPoints.query(np.array(SOMA_POINT), k=1)

        # Retrieve the RootNode coordinates
        RootNode = skeletonPoints[index]
        print('ROOT NODE', RootNode)
        del _allPoints
        print("Start Tree Construction")
        _autoTree = self.generateTree(RootNode, RootNode, skel.copy())

        return _autoTree

def distance(p1, p2): 
    d = math.sqrt(math.pow(p1[0]- p2[0], 2) +
                math.pow(p1[1] - p2[1], 2) +
                math.pow(p1[2] - p2[2], 2))
    return d

