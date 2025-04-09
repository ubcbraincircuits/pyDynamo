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
from scipy.stats import mode
import pydynamo_brain.util as util

from pydynamo_brain.model import *
from pydynamo_brain.ui.branchToColorMap import BranchToColorMap
from pydynamo_brain.util.util import douglasPeucker
from pydynamo_brain.util import imageCache
from pydynamo_brain.util import sortedBranchIDList
from .inference import modelPredict
from joblib import Parallel, delayed
from tqdm import tqdm 

_IMG_CACHE = util.ImageCache()

class TectalTracing():

    def __init__(self, parentActions, fullState, history):
        self.parentActions = parentActions
        self.state = fullState
        self.history = history
        self.branchToColorMap = BranchToColorMap()
        self.epislon_val = 1.5 #1.25
        self.xyzScale =  self.state.projectOptions.pixelSizes
        self.threshold = 10



    def findEndsAndJunctions(self, points, skelly_image):
        skelly_image[skelly_image>0]=1
        end_points = []
        y_points = []

        for point in range(points[0].shape[0]):
            i = points[0][point]
            j = points[1][point]
            window=skelly_image[i-1:i+2, j-1:j+2]

            if np.sum(window)<=2:
                end_points.append((j,i))
            if np.sum(window)==4:
                y_points.append((j,i))

            return end_points, y_points
    

    def _returnBranchPoints (self, skelFragment, skellID=1, ):
        factor = self.epislon_val
        points = np.where(skelFragment==skellID)
        points = np.array(points)
        points = [[_i[0], _i[1]] for _i in zip(points [0, :], points[1, :])]
        allPointTree = KDTree(points)
        sortedAllPoints = np.zeros_like(points)
        
        for i, c in enumerate(allPointTree.query(np.array(points[0]).reshape(1, -1), k=len(points))[1][0]):
            sortedAllPoints[i, : ] = points[c]

        reducedpoints = douglasPeucker(sortedAllPoints, factor)


        pointArray = np.array(reducedpoints)
        sortedPoints = np.zeros_like(pointArray)
        kdTree = KDTree(pointArray)
        for i, c in enumerate(kdTree.query(np.array([0,0]).reshape(1, -1), k=pointArray.shape[0])[1][0]):

            sortedPoints[i, : ] = pointArray[c, :]
        
        return sortedPoints
    
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


    def generateTree(self, somaCenter, skel):

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
            _nbrs = NearestNeighbors(n_neighbors=3, algorithm='brute').fit(junction_point_array)

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
            _nbrs = NearestNeighbors(n_neighbors=1, algorithm='brute').fit(junction_point_array)

            distances, indices = _nbrs.kneighbors(branch_array)
            if distances[:, 0][0] > 10:
                return None
            closest_branch_point_indices = indices[:, 0]

            closest_branch_points = tuple(junction_point_array[closest_branch_point_indices][0])

            
            return closest_branch_points

        # Current Tree method is too slow
        def returnClosetTreePoint(treeNbrs, treepoints, point):

            pointArray = np.array(point)
            distances, indices = treeNbrs.kneighbors(pointArray.reshape(1, -1))
            closest_point_indices = indices[:, 0]
            cloesestPoint = tuple(treepoints[closest_point_indices][0])
        
            return cloesestPoint

        skel[somaCenter[0], somaCenter[1], somaCenter[2]]=0
        # Find all of the branch nodes and ends in the dendrites
        end_points, y_points = self.find_skeleton_3Dpoints(skel)


        # Use DBSCAN to cluster nearby branch nodes (within 10 pixels)
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

        _somaNbrs = NearestNeighbors(n_neighbors=2, algorithm='brute').fit(end_pointArray)
        somaDists, somaIndex = _somaNbrs.kneighbors(somaCenter.reshape(1, -1))

        _closeBranchEnds = np.unique(end_pointArray[somaIndex[:, :]], axis=0)
        somaEndPoints = np.unique(_closeBranchEnds, axis=0)
        somaEnds = [tuple(_somaEnd) for _somaEnd in somaEndPoints[0]]

        endNodeSet = set(end_points)
        somaEndSet = set(somaEnds)
        _branchPoints = NearestNeighbors(n_neighbors=1, algorithm='brute').fit(_cleanBranchNodes)
        
        
        # Get the points of each branch and order them based on distance from an end or branching node
        # Currently slowest step
        # To-Do down sample point density with Douglas-Pecker here or when added to the tree
        _branchIds = np.unique(line_fragments)


        end_points_array = np.array(end_points)
        skel_shape = skel.shape
        end_indices = np.ravel_multi_index((end_points_array[:,0], end_points_array[:,1], end_points_array[:,2]), skel_shape)

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

        def process_branch(_id):
            if _id <= 0:
                return None
            _coords = np.where(line_fragments == _id)
            branchPoints_array = np.column_stack(_coords)


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
                branch_path = chunked_douglas_peucker(branch_path, 3, 100)
            return branch_path
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
        
        
        orderedBranches = Parallel(n_jobs=-1)(
            delayed(process_branch)(_id) for _id in tqdm(_branchIds)
        )
        orderedBranches = [branch for branch in orderedBranches if branch is not None]

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
                    _points.insert(0, (somaCenter[0], somaCenter[1], somaCenter[2]))
                    junction = returnBranchingNode(_points, _cleanBranchNodes)
                    junctionsInTree.append(junction)
                    _points.append(junction)
                    TreeBranches.append(_points) 
                    _ = _orderedBranches.pop(_orderedBranches.index(_points))
  
                else:                                  
                    _points =  orderPointList(_endNode, _points)
                    _points.insert(0, (somaCenter[0], somaCenter[1], somaCenter[2]))
                    junction = returnBranchingNode(_points, _cleanBranchNodes)
                    junctionsInTree.append(junction)
                    TreeBranches.append(_points) 
                    _ =_orderedBranches.pop(_orderedBranches.index(path))

        # Tree Object to assemble 
        newTree = Tree()
        newTree._parentState = self.state.uiStates[0]
        
        # List to hold points added to the tree
        _TreePoints = []

        _TreePoints.append(tuple([int(somaCenter[2]), int(somaCenter[1]), int(somaCenter[0])]))
        rootNode = Point(id='root', 
                        location=tuple([int(somaCenter[2]), int(somaCenter[1]), int(somaCenter[0])]))
        newTree.rootPoint = rootNode
        newTree.rootPoint.parentBranch = None 
        
        # Replace with normal branchID and PointID in the future 
        _branchNum = 0
        _pointNum =  1

        # Add basal and primary dendrite
        for _path in TreeBranches:
            _path = self.DouglasPeucker3D(_path, self.epislon_val)
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
                
        # Initialize NearestNeighbors for points in tree
        _treePointArr = np.array(_TreePoints)
        _nbrsTree = NearestNeighbors(n_neighbors=1, algorithm='brute').fit(_treePointArr)

        
        
        # CloestPointTo is super slow! Replace with nearestneighbor algo? 
        remainingBranches = -1
        failures = 0
        while failures < 25:
            _treePointArr = np.array(_TreePoints)
            _nbrsTree = NearestNeighbors(n_neighbors=1, algorithm='brute').fit(_treePointArr)
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
                        _closestTreeNode = returnClosetTreePoint(_nbrsTree, _treePointArr, _points[0])
                        if distance_3d(_closestTreeNode, _points[0]) < 10:
                            
                            
                            _parentNode = newTree.closestPointTo((int(_closestTreeNode[2]), int(_closestTreeNode[1]), int(_closestTreeNode[0])))
                            #_p_pointsath = self.DouglasPeucker3D(_points, self.epislon_val)

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
                            _nbrsTree = NearestNeighbors(n_neighbors=1, algorithm='brute').fit(_treePointArr)
                else:
                    _closestTreeNode = returnClosetTreePoint(_nbrsTree, _treePointArr, _points[0])
                    if distance_3d(_closestTreeNode, _points[0]) > 10:
                        _closestTreeNode = returnClosetTreePoint(_nbrsTree, _treePointArr, _points[-1])  
                    if distance_3d(_closestTreeNode, _points[-1]) < 10:
                            _points.reverse()
                    if distance_3d(_closestTreeNode, _points[0]) < 10:
                        _points = self.DouglasPeucker3D(_points, self.epislon_val)

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
                        _nbrsTree = NearestNeighbors(n_neighbors=1, algorithm='brute').fit(_treePointArr)
            if len(_orderedBranches) == remainingBranches:
                failures += 1
        newTree.updateAllPrimaryBranches()
        print("Branches in tree:", len(newTree.branches))
        for branch in newTree.branches:
            if branch.worldLengths()[0] < 5:
                if branch.hasChildren() == False:
                    reverseIndex = list(reversed(range(len(branch.points))))
                    for i in reverseIndex:
                        newTree.removePointByID(branch.points[i].id)
        newTree.updateAllPrimaryBranches()
        print("Branches in tree:", len(newTree.branches))
        return newTree
       
  
    def dendriteTracing(self):
        if self.state.trees[0].rootPoint !=None:
            print("Tree already present")
            return
        
        # TODO Pull in image from imageChache
        volume = _IMG_CACHE.getVolume(self.state.uiStates[0].imagePath)

        # Work with the current channel
        #imgVolume = volume[self.state.channel,:,:,:]
        def _postProcess(image):
            image = image.astype(np.float64) ** 0.75 # Gamma correction
            for c in range(image.shape[0]):
                for i in range(image.shape[1]):
                    d = image[c, i]
                    mn = np.percentile(d, 10)
                    mx = np.max(d)
                    image[c, i] = 255 * (d - mn) / (mx - mn)
            return np.round(image.clip(min=0)).astype(np.uint8)
        imgVolume = _postProcess(gaussian(volume[self.state.channel,:,:,:].astype(np.float16), .15))
        for imgSlice in range(imgVolume.shape[0]):
            imgVolume[imgSlice, :,:] -= mode(imgVolume[imgSlice, :,:])[0].astype(np.uint8)
        imgVolume[imgVolume < 0] = 0
        # IMAGE [z, x , y]
        pixelClasses, other = modelPredict(imgVolume.astype(np.uint8),"Soma+Dendrite")
        soma = pixelClasses[:,:,:].copy()
        soma[pixelClasses[:,:,:]!=1]=0
        soma = np.array(soma, bool)
        
        mask_int = soma.astype(int)  
        # Use the largest group of pixels as the soma
        labeled_array = label(mask_int, connectivity=soma.ndim)
        regions = regionprops(labeled_array)
        largest_region = max(regions, key=lambda r: r.area)
        largest_component = (labeled_array == largest_region.label)

        soma = (labeled_array == largest_region.label)
        
        # Center of soma pixels
        SOMA_POINT = center_of_mass(soma)

        dendrites = np.zeros_like(pixelClasses[:,:,:])
        dendrites[pixelClasses[:,:,:]==2]=1
        dendrites = np.array(dendrites, bool)

        # Filter out small false positive pixels
        dendrites = remove_small_objects(dendrites, 500, connectivity=10)
       
       
        neuron = np.zeros_like(dendrites)
        neuron[dendrites == 1] = 1
        neuron = neuron.astype(np.float16)

        neuron = gaussian(neuron, 0.5)
        neuron = neuron.astype(np.float16)
        soma_gaussian = gaussian(soma.astype(np.float16))
        neuron += soma_gaussian
        neuron = np.clip(neuron, 0, 1)


        # Create a skeleton of the dendrites #spooky
        skel = skeletonize_3d(neuron)
        skel = skel.astype(np.int8)


        skeletonPoints = np.array(np.where(skel==np.max(skel)))
        _allPoints = NearestNeighbors(n_neighbors=1, algorithm='brute').fit(skeletonPoints.T)
        somaDists, somaIndex = _allPoints.kneighbors(np.array(SOMA_POINT).reshape(1, -1))

        RootNode = skeletonPoints.T[somaIndex, :][0][0]

        _autoTree = self.generateTree(RootNode, skel.copy())

        return _autoTree

def angle_between_vectors(A, B, C):
    # Calculate vectors AB and AC
    vector_AB = np.array(B) - np.array(A)
    vector_AC = np.array(C) - np.array(A)
    
    # Calculate the dot product of vectors AB and AC
    dot_product = np.dot(vector_AB, vector_AC)
    
    # Calculate the magnitude (norm) of vectors AB and AC
    magnitude_AB = np.linalg.norm(vector_AB)
    magnitude_AC = np.linalg.norm(vector_AC)
    
    # Calculate the cosine of the angle between vectors AB and AC
    cosine_theta = dot_product / (magnitude_AB * magnitude_AC)
    cosine_theta = np.clip(cosine_theta, -1, 1)
    
    
    angle_rad = np.arccos(cosine_theta)


    # Convert the angle to degrees
    angle_deg = np.degrees(angle_rad)

    return angle_deg

def distance(p1, p2): 
    d = math.sqrt(math.pow(p1[0]- p2[0], 2) +
                math.pow(p1[1] - p2[1], 2) +
                math.pow(p1[2] - p2[2], 2))
    return d

