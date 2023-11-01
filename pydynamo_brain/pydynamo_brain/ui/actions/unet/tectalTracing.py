import numpy as np
import random
import math
from skimage.measure import label
from skimage.filters import sobel
from skimage.morphology import skeletonize_3d, dilation, erosion, remove_small_objects
from skimage.segmentation import watershed, random_walker, expand_labels
from sklearn.neighbors import NearestNeighbors, KDTree

from scipy.ndimage import center_of_mass

import pydynamo_brain.util as util

from pydynamo_brain.model import *
from pydynamo_brain.ui.branchToColorMap import BranchToColorMap
from pydynamo_brain.util.util import douglasPeucker
from pydynamo_brain.util import imageCache
from pydynamo_brain.util import sortedBranchIDList
from .inference import modelPredict

_IMG_CACHE = util.ImageCache()

class TectalTracing():

    def __init__(self, parentActions, fullState, history):
        self.parentActions = parentActions
        self.state = fullState
        self.history = history
        self.branchToColorMap = BranchToColorMap()
        self.epislon_val = 1.2



    def segmentedSkeleton(self, img2skel):
        # Takes an skeletonized image and segments the skeleton per plane
        # Returns segments as unique values in 3D array
        skel = skeletonize_3d(img2skel)
    
        segsPerPlane = np.zeros(img2skel.shape)
        foreground, background = 1, 2

        for i in range(skel.shape[0]):

            edges = sobel(skel[i,:,:])
            plane = skel[i,:,:]
            
            seeds = np.zeros((512,512))
            
            seeds[plane <.5] = background
            seeds[skel[i,:,:] > .5] = foreground
            ws = watershed(edges, seeds)
            segments = label(ws == foreground)
            temp_max = np.max(segsPerPlane)
            segments = segments+temp_max
            segments[segments ==temp_max]=0
            segsPerPlane[i,:,:] = segments
        
        return segsPerPlane, skel

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
    
    def filterPoints(p1, p2, listofpoints):
        filteredPoints = []
        imageSpace = []
        for point in listofpoints:
            imageSpace.append((int(point[0]/5), int(point[1]*1.0), int(_path[2]/1.0)))
        # TODO Get image dim 
        np.zeros(120, 512, 512)
        
        
        return filteredPoints

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
    

    def generateTree(self, somaCenter, somaCloud, branchData):
        newTree = Tree()
        newTree._parentState = self.state.uiStates[0]
        
        # Root the tree
        somaCenter = list(somaCenter)
        somaCenter[0] = somaCenter[0]*6.25
        somaCenter = np.round(somaCenter)
        somaPoint =  Point(
                            id ='root',
                            location = tuple((somaCenter[2]*1.0, somaCenter[1]*1.0, somaCenter[0]/6.25))
                            
                                )

        newTree.rootPoint = somaPoint
        newTree.rootPoint.parentBranch = None                        
        secondaryBranchPool = []


        _pointPool = branchData.copy()
        unique_tuples = set()
        _pointPool = [tup for tup in _pointPool if not (tup in unique_tuples or unique_tuples.add(tup))]
        _parentPoints = {}

        # Create Tree Search Space and Add Soma
        _treeSearchSpace = []
        _treeSearchSpace.append(np.round(tuple(np.round(somaCenter))))


        _branchPaths = []
        _inspectedPoints = []
        PrimaryBranch = True

        _somaNbrs = NearestNeighbors(n_neighbors=3, algorithm='brute').fit(somaCloud)
        print('Primary Branch Search... this may take a minute')
        while PrimaryBranch == True:
            if PrimaryBranch == False:
                break
            firstPoint = True
            Complete = False
            path = []
            _lastSearch = len(_pointPool)
            while Complete == False:
        
                if firstPoint:
                    
                    path.append(_treeSearchSpace[0])
                    random.shuffle(_pointPool)
                    for _point in _pointPool:
                        distances, indices = _somaNbrs.kneighbors(np.array(_point).reshape(1, -1))
                        if distances[0][0] < 15:

                            _rootNode = _treeSearchSpace[0]
                            _currentPoint = _point
                            path.append(_currentPoint)
                            _parentPoints[_currentPoint] = _rootNode
                            _treeSearchSpace.append(_currentPoint)
                            _pointPool.pop(_pointPool.index(_point))
                            firstPoint = False
                            break
                    if firstPoint == False:
                        break
                    if _lastSearch ==  len(_pointPool):
                        Complete == True
                        break

                            
                
                else:
                    if len(_pointPool) > 10:
                        _nbrs = NearestNeighbors(n_neighbors=10, algorithm='brute').fit(_pointPool)
                        distances, indices = _nbrs.kneighbors(np.array(_currentPoint).reshape(1, -1))
                        for _idx in range(10):
                        
                            if distances[0][_idx] < 20:
                            
                                if angle_between_vectors(_rootNode, _currentPoint, _pointPool[indices[0][_idx]]) < 90:
                                    _pointIndex = indices[0][_idx]
                                    _parentPoints[_currentPoint] = _rootNode
                                    _rootNode = _currentPoint
                                    _currentPoint = _pointPool[_pointIndex]
                                    _parentPoints[_currentPoint] = _rootNode
                                    path.append( _pointPool[_pointIndex])
                                    _treeSearchSpace.append(_currentPoint)
                                    _pointPool.pop(_pointIndex)
                                    break
                        else:
                            Complete = True
                            _lastSearch = len(_pointPool)

                    
                    else:
                        Complete = True
                        _lastSearch = len(_pointPool)
                        
            if len(_pointPool) == _lastSearch:
                PrimaryBranch = False
                Complete == True
            if len(path)>2:
                _branchPaths.append(path)
            else:
                for _removed in _branchPaths[1:]:
                    _popi = _treeSearchSpace.index(_removed)
                    secondaryBranchPool.append( _treeSearchSpace.pop(_popi))
                    
            
        PrimaryBranch == False

        print('Secondary branch search... this may take a minute')
        _pointPool += secondaryBranchPool
        _catche =  len(_pointPool)+1


        secondaryBranch = True
        while secondaryBranch:
            firstPoint = True
            Complete = False
            path = []

            while Complete == False:
                if _catche == len(_pointPool):
                    secondaryBranch = False
                    Complete = True
                    break

                if firstPoint:
                    _catche = len(_pointPool)
                    random.shuffle(_pointPool)
                    if len(_treeSearchSpace)>3:
                        _treeNbrs = NearestNeighbors(n_neighbors=3, algorithm='brute').fit(_treeSearchSpace)
                        for _nbIndex, _newBranch in enumerate(_pointPool):
                            if firstPoint:
                                distances, indices = _treeNbrs.kneighbors(np.array(_newBranch).reshape(1, -1))
                                if distances[0][0] < 20:
                                    _rootNode = _treeSearchSpace[indices[0][0]] # _newBranch
                                    _currentPoint = _newBranch
                                    _treeSearchSpace.append(_currentPoint)
                                    path.append(_rootNode)
                                    path.append(_currentPoint)
                                    _parentPoints[_currentPoint] = _rootNode
                                    _null = _pointPool.pop(_nbIndex)
                                    firstPoint = False


                else:
                    if len(_pointPool) > 10:
                        _nbrs = NearestNeighbors(n_neighbors=10, algorithm='brute', n_jobs=3).fit(_pointPool)
                        distances, indices = _nbrs.kneighbors(np.array(_currentPoint).reshape(1, -1))
                        for _idx in range(10):
                            if distances[0][_idx] < 20:
                                if angle_between_vectors(_rootNode, _currentPoint, _pointPool[indices[0][_idx]]) < 30:
                                    _pointIndex = indices[0][_idx]
                                    _parentPoints[_currentPoint] = _rootNode
                                    _rootNode = _currentPoint
                                    _currentPoint = _pointPool[_pointIndex]
                                    path.append( _pointPool[_pointIndex])
                                    _treeSearchSpace.append(_currentPoint)
                                    _pointPool.pop(_pointIndex)
                                    break
                        if _idx == 9:
                            Complete = True
                            _branchPaths.append(path)
                            path = []
                    else:
                            Complete = True
                            _branchPaths.append(path)
                            path = []




        _pointNum = 1
        _branchNum = 1
        for _path in _branchPaths:
                
                _parentNode = newTree.closestPointTo((_path[0][2]*1.0, _path[0][1]*1.0, int(_path[0][0]/6.25)))
                _ = _path.pop(0)
                newBranch = Branch(id = 'b'+str(_branchNum))
                _branchNum += 1
                for xyz in _path:                    
                    nextPoint = Point(
                            id = 'p'+str(_pointNum),
                            location = tuple((xyz[2]*1.0, xyz[1]*1.0, int(xyz[0]/6.25)))
                            )
                    _pointNum += 1 
                    newBranch.addPoint(nextPoint)
                    
                newBranch.setParentPoint(_parentNode)
                newTree.addBranch(newBranch)
                #_branchList.append(newBranch)

        return newTree
        
    




    def dendriteTracing(self):
        if self.state.trees[0].rootPoint !=None:
            print("Tree already present")
            return
        
        # TODO Pull in image from imageChache
        volume = _IMG_CACHE.getVolume(self.state.uiStates[0].imagePath)

        # Work with the current channel
        imgVolume = volume[self.state.channel,:,:,:]

   
        # IMAGE [z, x , y]
        pixelClasses, other = modelPredict(imgVolume,"Soma+Dendrite", 2)

        soma = pixelClasses[0,:,:,:].copy()
        soma[pixelClasses[0,:,:,:]!=1]=0
        soma = np.array(soma, bool)

        # Filter out small false positive pixels
        soma = remove_small_objects(soma,300, connectivity=2)

        dendrites = np.zeros_like(pixelClasses[0,:,:,:])
        dendrites[pixelClasses[0,:,:,:]==2]=1
        dendrites = np.array(dendrites, bool)

        # Filter out small false positive pixels
        dendrites = remove_small_objects(dendrites, 500, connectivity=10)
        dendrites[soma!=0]=0


        segsperplane, _ = self.segmentedSkeleton(dendrites)
        
        branch_key = 0
        branches = {}
        allPoints = {}
        for z in range(segsperplane.shape[0]):
                
            segs_colors = np.unique(segsperplane[z,:,:]).astype(int)
                    
            _endPoints= []
            for i in segs_colors:
                branches[branch_key] = []
                if i>0:
                    _endPoints= []
                    plane = segsperplane[z,:,:].copy()

                    plane[plane !=i]=0
                    plane[plane>0]=1
                    points = np.where(plane==1)

                    points, junctions = self.findEndsAndJunctions(points, plane)

                    if len(junctions) >0:
                        for junc in junctions:
                            plane[junc[1], junc[0]] =0
                        
                        line_fragments = label(plane)
                        cut_lines = np.unique(line_fragments).astype(int)
                        for line in cut_lines[1:]:
                            _endPoints = []
                            plane = line_fragments.copy()
                            plane[plane !=line]=0
                            plane[plane>0]=1
                            points = np.where(plane==1)
                            points, junctions = self.findEndsAndJunctions(points, plane)
                            if len(points)>1:
                                for point in points:
                                    _endPoints.append((z, point[1], point[0]))
                                
                                branches[branch_key] = _endPoints
                                allPoints[branch_key] = self._returnBranchPoints(plane)
                                branch_key += 1
                                
                                
                            else: 
                                for point in points:
                                    _endPoints.append((z, point[1], point[0]))
                                    allPoints[branch_key] = np.reshape(np.array([point[1], point[0]]), (1,2))
                                branches[branch_key] = _endPoints
                                branch_key += 1

                        
                    else:
     
                        if len(points)>1:
                            for point in points:
                                _endPoints.append((z, point[1], point[0]))
                            branches[branch_key] = _endPoints
                            allPoints[branch_key] = self._returnBranchPoints(plane)
                            branch_key += 1
                        else:
                            for point in points:
                                _endPoints.append((z, point[1], point[0]))
                                allPoints[branch_key] = np.reshape(np.array([point[1], point[0]]), (1,2))
                            branches[branch_key] = _endPoints
                            branch_key += 1
        


        for key in list(allPoints.keys()):
            if len(allPoints) < 2:
                del allPoints
            else:
                   
                z_value = np.zeros((allPoints[key].shape[0], 1+allPoints[key].shape[1]))
                # TODO use project XYZ scaling
                z_value[:, 0] = branches[key][0][0]*6.25
                z_value[:, 1:] = allPoints[key]
                allPoints[key] = z_value
        
        allPoints3D = []
        for key in allPoints.keys():
            for i in range(allPoints[key].shape[0]):
                # TODO pull in project XYZ scale
                allPoints3D.append((allPoints[key][i,0], allPoints[key][i,1], allPoints[key][i,2]))
        

        
        
        SOMA_POINT = center_of_mass(soma)
        soma_filter = expand_labels(soma, distance=3)
        _z, _x, _y = np.where(soma_filter==1)
        _somaCoords = list( zip(_z*6.25, _x, _y))
        _somaCloudindex = np.random.choice(len(_somaCoords), int(.05*len(_somaCoords)), replace=False)
        _somaCloud = [_somaCoords[i] for i in _somaCloudindex]



        _autoTree = self.generateTree(SOMA_POINT, _somaCloud, allPoints3D)

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
    
    # Calculate the angle in radians using arccosine
    angle_rad = np.arccos(cosine_theta)
    
    # Convert the angle to degrees
    angle_deg = np.degrees(angle_rad)

    return angle_deg

def distance(p1, p2): 
    print(p1, p2, '\n')
    d = math.sqrt(math.pow(p1[0]- p2[0], 2) +
                math.pow(p1[1] - p2[1], 2) +
                math.pow(p1[2] - p2[2], 2))
    return d

