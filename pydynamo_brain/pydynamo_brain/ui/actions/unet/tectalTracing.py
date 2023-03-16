import numpy as np

from skimage.measure import label
from skimage.filters import sobel
from skimage.morphology import skeletonize_3d, dilation, erosion, remove_small_objects
from skimage.segmentation import watershed, random_walker
from sklearn.neighbors import NearestNeighbors, KDTree

from scipy.ndimage import center_of_mass

import pydynamo_brain.util as util

from pydynamo_brain.model import *
from pydynamo_brain.ui.branchToColorMap import BranchToColorMap
from pydynamo_brain.util.util import douglasPeucker
from pydynamo_brain.util import imageCache
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
    

    def generateTree(self, somaCenter, branchData):
        newTree = Tree()
        newTree._parentState = self.state.uiStates[0]
        
        # Root the tree
        somaCenter = list(somaCenter)
        somaCenter[0] = somaCenter[0]*5
        somaCenter = np.round(somaCenter)
        somaPoint =  Point(
                            id ='root',
                            location = tuple((somaCenter[2]*1.0, somaCenter[1]*1.0, somaCenter[0]/5.0))
                            
                                )

        newTree.rootPoint = somaPoint
        newTree.rootPoint.parentBranch = None                        
   
        _pointNum = 1
        _branchNum = 1

        # Loop over other basal branches
        _endPoints = branchData.copy()
        _matchedPath = [] 
        _treeSearchSpace = []
        SOMA_RADIUS = 60
        GAP = 15
        _branchList = []


        _branchPaths = []
        for i in range(5):
            firstPoint = True
            Complete = False
            path = []
            # Find path with nearest neighbor search
            while Complete == False:
                nbrs = NearestNeighbors(n_neighbors=3, algorithm='brute').fit(_endPoints)
                if firstPoint:
                    distances, indices = nbrs.kneighbors(np.array(somaCenter).reshape(1, -1))

                    if distances[0][0] < SOMA_RADIUS:
                        path.append(_endPoints[indices[0][0]])
                        _currentPoint = _endPoints[indices[0][0]]
                        
                        _endPoints.pop(indices[0][0])
                        firstPoint = False
                    else:
                        break
                else:
                    distances, indices = nbrs.kneighbors(np.array(_currentPoint).reshape(1, -1))
                    if distances[0][0] < GAP:
                        path.append(_endPoints[indices[0][0]])
                        _currentPoint = _endPoints[indices[0][0]]
                        _treeSearchSpace.append(_endPoints[indices[0][0]])
                        _endPoints.pop(indices[0][0])
                    else:
                        Complete = True

            _branchPaths.append(path)
            if len(path)>0:
                newBranch = Branch(id = 'b'+str(_branchNum))
                _branchNum += 1
                for xyz in path:                    
                    nextPoint = Point(
                            id = 'p'+str(_pointNum),
                            location = tuple((xyz[2]*1.0, xyz[1]*1.0, int(xyz[0]/5.0)))
                            )
                    _pointNum += 1 
                    newBranch.addPoint(nextPoint)
                    
                newBranch.setParentPoint(somaPoint)
                newTree.addBranch(newBranch)
                _branchList.append(newBranch)

         
        _parentPoints = []
        _childBranches = []
        GAP = 15

        #return newTree
        # Find non-basal branches

        while len(_endPoints)>3:
            firstPoint = True
            Complete = False
            path = []
            while Complete == False:
                nbrs = NearestNeighbors(n_neighbors=3, algorithm='brute').fit(_endPoints)
                if firstPoint:
                    distances, indices = nbrs.kneighbors(np.array(somaCenter).reshape(1, -1))
                    
                   
                    path.append(_endPoints[indices[0][0]])
                    _currentPoint = _endPoints[indices[0][0]]

                    _parentNbrs = NearestNeighbors(n_neighbors=3, algorithm='brute').fit(_treeSearchSpace)
                    distances, _parentNode = _parentNbrs.kneighbors(np.array(_currentPoint).reshape(1, -1))
                    _parentPoints.append(_treeSearchSpace[_parentNode[0][0]])
                    _endPoints.pop(indices[0][0])
                        
                    firstPoint = False


                else:
                    if len(_endPoints)>3:
                        distances, indices = nbrs.kneighbors(np.array(_currentPoint).reshape(1, -1))
                        if distances[0][0] < GAP:
                            path.append(_endPoints[indices[0][0]])
                            _currentPoint = _endPoints[indices[0][0]]
                            _treeSearchSpace.append(_endPoints[indices[0][0]])
                            _endPoints.pop(indices[0][0])
                        else:
                            Complete = True
                    else:
                        Complete = True
            _childBranches.append(path)
        
        for _path in zip(_childBranches, _parentPoints):
                path = _path[0]
                _parentNode = newTree.closestPointTo((_path[1][2]*1.0, _path[1][1]*1.0, int(_path[1][0]/5.0)))
                
                newBranch = Branch(id = 'b'+str(_branchNum))
                _branchNum += 1
                for xyz in path:                    
                    nextPoint = Point(
                            id = 'p'+str(_pointNum),
                            location = tuple((xyz[2]*1.0, xyz[1]*1.0, int(xyz[0]/5.0)))
                            )
                    _pointNum += 1 
                    newBranch.addPoint(nextPoint)
                    
                newBranch.setParentPoint(_parentNode)
                newTree.addBranch(newBranch)
                _branchList.append(newBranch)
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
        soma = remove_small_objects(soma,250, connectivity=2)

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
        


        for key in allPoints.keys():
            allPoints[key]
            z_value = np.zeros((allPoints[key].shape[0], 1+allPoints[key].shape[1]))
            # TODO use project XYZ scaling
            z_value[:, 0] = branches[key][0][0]*5
            z_value[:, 1:] = allPoints[key]
            allPoints[key] = z_value
        
        allPoints3D = []
        for key in allPoints.keys():
            for i in range(allPoints[key].shape[0]):
                # TODO pull in project XYZ scale
                allPoints3D.append((allPoints[key][i,0], allPoints[key][i,1], allPoints[key][i,2]))
        

        
        
        SOMA_POINT = center_of_mass(soma)




        _autoTree = self.generateTree(SOMA_POINT, allPoints3D)
        return _autoTree

