import numpy as np
import matplotlib.pyplot as plt
import scipy.optimize
from scipy.ndimage.filters import gaussian_filter
from skimage import transform as tf

import util
from files import ImageCache

WARP_MODE = 'edge'

_IMG_CACHE = ImageCache()

def centreRotation(shape, R, T):
    (x, y) = shape
    dx, dy = (x - 1) // 2, (y - 1) // 2
    tf_rotate = tf.SimilarityTransform(rotation=R)
    tf_shift = tf.SimilarityTransform(translation=[-dx, -dy])
    tf_shift_inv = tf.SimilarityTransform(translation=[dx + T[0], dy + T[1]])
    return tf_shift + tf_rotate + tf_shift_inv

def UINT8_WARP(image, transform):
    assert image.dtype == np.uint8
    warpDouble = tf.warp(image, transform, mode=WARP_MODE)
    assert warpDouble.dtype == np.float64
    return np.round(warpDouble * 255).astype(np.uint8)

def recursiveAdjust(fullState, id, branch, point, pointref, Rxy=30, Rz=4):
    """
    recursively adjusts points, i.e. the 'R' function
    id       -image on which to adjust (reference is id-1)
    branch   -the branch being adjusted
    point    -point in id being adjusted
    pointref -point in id-1 being adjusted

    Rxy      -radius, in pixels, of field to be compared
    Rz       -radius, in z axis, of field to be compared
    """

    newTree = fullState.uiStates[id]._tree
    dLoc = (Rxy, Rxy, Rz)

    # extract the 'boxes'; subimages for alignment
    xyz = pointref.location
    xyz = (int(np.round(xyz[0])), int(np.round(xyz[1])), int(np.round(xyz[2])))
    oldLocMin = util.locationMinus(xyz, dLoc)
    oldLocMax = util.locationPlus(xyz, dLoc)
    volume = _IMG_CACHE.getVolume(fullState.uiStates[id - 1].imagePath)
    oldBox = _imageBoxIfInside(volume, fullState.channel, oldLocMin, oldLocMax)
    if oldBox is None:
        _recursiveHilight(newTree, branch, fromPointIdx=point.indexInParent())
        return

    xyz = point.location
    xyz = (int(np.round(xyz[0])), int(np.round(xyz[1])), int(np.round(xyz[2])))
    newLocMin = util.locationMinus(xyz, dLoc)
    newLocMax = util.locationPlus(xyz, dLoc)
    volume = _IMG_CACHE.getVolume(fullState.uiStates[id].imagePath)
    newBox = _imageBoxIfInside(volume, fullState.channel, newLocMin, newLocMax)
    if newBox is None:
        _recursiveHilight(newTree, branch, fromPointIdx=point.indexInParent())
        return

    # align the z-projected images in XY
    opt = {
        'Similarity': 'p',
        'Registration': 'Rigid',
        'Verbose': 0,
    }
    Bx, By, angle, fval = _registerImages(np.max(oldBox, axis=2), np.max(newBox, axis=2), opt)
    I1 = np.mean(oldBox.astype(np.int32) ** 2)
    I2 = np.mean(newBox.astype(np.int32) ** 2)

    # the alignment is poor; give up!
    fTooBad = (fval is None) or fval > (max(I1,I2)*0.9)
    print ("%f, %f > %f, %f > %f, %f > %f" % (abs(angle), fval, (max(I1,I2)*0.9), abs(Bx[Rxy+1,Rxy+1]), Rxy * 0.8, abs(By[Rxy+1,Rxy+1]), Rxy * 0.8))
    xMoveTooFar = np.abs(Bx[Rxy+1,Rxy+1]) > (Rxy*0.8)
    yMoveTooFar = np.abs(By[Rxy+1,Rxy+1]) > (Rxy*0.8)
    if (np.abs(angle) > 0.3 or fTooBad or xMoveTooFar or yMoveTooFar):
        print ("Bad fit! larger window if %d < 25" % Rxy)
        if Rxy < 25: # try a larger window
            recursiveAdjust(fullState, id, branch, point, pointref, 25, 4)
        else:
            _recursiveHilight(newTree, branch, fromPointIdx=point.indexInParent())
        return

    # Find optimal Z-offset for known 2d alignment
    mX, mY, mZ = np.dstack([Bx] * (2*Rz + 1)), np.dstack([By] * (2*Rz + 1)), np.zeros(oldBox.shape)
    oldBoxShifted = _movePixels(oldBox, mX, mY, mZ)

    bestZ, bestZScore = None, 0
    for dZ in range(-Rz, Rz + 1):
        xyNewZ = (xyz[0], xyz[1], xyz[2] + dZ)
        newLocMinZ = util.locationMinus(xyNewZ, dLoc)
        newLocMaxZ = util.locationPlus(xyNewZ, dLoc)
        newBoxZ = _imageBoxIfInside(volume, fullState.channel, newLocMinZ, newLocMaxZ)
        if newBoxZ is None:
            continue
        delta = _imageDifference(oldBoxShifted, newBoxZ)
        score = delta * (6 + abs(dZ) ** 1.1)
        if bestZ is None or bestZScore > score:
            bestZ, bestZScore = dZ, score
    # print ("Best Z is %d, delta = %d, score = %f" % (xyz[2] + bestZ, bestZ, bestZScore))

    shiftX = -By[Rxy, Rxy]
    shiftY = -Bx[Rxy, Rxy]
    shiftZ = bestZ # minIdx - Rz - 1
    shift = (shiftX, shiftY, shiftZ)
    print('Point at (%.3f, %.3f, %.3f), best angle %.4f, moving branch by: (%.3f, %.3f, %.3f)' % \
        (point.location[0] + 1, point.location[1] + 1, point.location[2] + 1, angle, shiftX, shiftY, shiftZ))

    # Point successfully registered to Pointref!
    point.id = pointref.id
    _recursiveMoveBranch(newTree, branch, shift, fromPointIdx=point.indexInParent())

    nextPoint = point.nextPointInBranch()
    nextPointRef = pointref.nextPointInBranch()
    if nextPoint is not None and nextPointRef is not None:
        deltaXYZ = np.abs(util.locationMinus(nextPoint.location, point.location))
        dXY = int(round(util.snapToRange(np.max(deltaXYZ[0:1]), 20, 30)))
        dZ = int(round(util.snapToRange(deltaXYZ[2], 2, 4) + 1))
        recursiveAdjust(fullState, id, branch, nextPoint, nextPointRef, dXY, dZ)

    # TODO - match up branches properly
    for branch in point.children:
        for i in range(min(len(point.children), len(pointref.children))):
            branch, branchRef = point.children[i], pointref.children[i]
            recursiveAdjust(fullState, id, branch, branch.points[0], branchRef.points[0])


def _recursiveMoveBranch(tree, branch, shift, fromPointIdx=0):
    # TODO: make recursiveMovePoint?
    if branch is None: # Root branch
        pointToMove = tree.rootPoint
        pointToMove.location = util.locationPlus(pointToMove.location, shift)
        for childBranch in tree.branches:
            _recursiveMoveBranch(tree, childBranch, shift)

    else:
        for pointToMove in branch.points[fromPointIdx:]:
            pointToMove.location = util.locationPlus(pointToMove.location, shift)
            for childBranch in pointToMove.children:
                _recursiveMoveBranch(tree, childBranch, shift)

def _recursiveHilight(tree, branch, fromPointIdx=0):
    if branch is None:
        for point in tree.flattenPoints():
            point.hilighted = True
    else:
        for pointToHilight in branch.points[fromPointIdx:]:
            pointToHilight.hilighted = True
            for childBranch in pointToHilight.children:
                _recursiveHilight(tree, childBranch)

def _imageBoxIfInside(volume, channel, fr, to):
    to = util.locationPlus(to, (1, 1, 1)) # inclusive to exclusive upper bounds
    s = volume.shape # (channels, stacks, x, y)
    volumeXYZ = (s[2], s[3], s[1])
    for d in range(3): # Verify the box fits inside the volume:
        if fr[d] < 0 or volumeXYZ[d] < to[d]:
            return None
    subVolume = volume[channel, fr[2]:to[2], fr[1]:to[1], fr[0]:to[0]] # ZYX
    subVolume = np.moveaxis(subVolume, 0, -1) # YXZ
    return subVolume

def _registerImages(movingImg, staticImg, opt, drawTitle=False):
    assert movingImg.shape == staticImg.shape
    # Make smooth images for histogram and fast affine registration
    movingImgSmooth = _imgGaussian(movingImg, 1.5)
    staticImgSmooth = _imgGaussian(staticImg, 1.5)

    # % Set initial affine parameters
    # x = [0, 0, 0]
    x = [0.5761, -5.8860, -0.1057]

    def _affineRegistrationError(x):
        return _affineError(x, movingImgSmooth, staticImgSmooth)

    # 'MaxIter',100,'MaxFunEvals',1000,'TolFun',1e-10,'DiffMinChange',1e-6);
    opt = {
        # 'maxiter': 100,
        # 'maxfun': 1000,
        'ftol': 1e-6,
        'disp': False,
        # 'eps': 1e-6
    }
    # method = 'L-BFGS-B'
    # method = 'BFGS'
    method = 'Nelder-Mead'
    res = scipy.optimize.minimize(_affineRegistrationError, x, tol=1e-4, method=method, options=opt)
    if not res.success:
        print (res.message)
        raise Exception("COULD NOT OPTIMIZE!")
    x = res.x

    trans = centreRotation(staticImgSmooth.shape, R=x[2], T=(x[1], x[0]))
    M = trans.params
    warpedImgSmooth = UINT8_WARP(movingImgSmooth, trans)
    fval = _imageDifference(staticImgSmooth, warpedImgSmooth)

    x, y = np.meshgrid(range(movingImg.shape[0]), range(movingImg.shape[1]))
    xd = x - (movingImg.shape[0]/2)
    yd = y - (movingImg.shape[1]/2)
    M[0, 2] = res.x[0]
    M[1, 2] = res.x[1]
    Bx = ((movingImg.shape[0]/2) + M[0, 0] * xd + M[0, 1] * yd + M[0, 2] * 1) - x;
    By = ((movingImg.shape[1]/2) + M[1, 0] * xd + M[1, 1] * yd + M[1, 2] * 1) - y;
    angle = trans.rotation

    if drawTitle:
        title = "Best: %s (score %f)" % (str(res.x), fval)
        f, (ax1, ax2, ax3) = plt.subplots(1, 3)
        f.suptitle(title)
        ax1.imshow(movingImgSmooth.astype(np.float), cmap='gray')
        ax2.imshow(staticImgSmooth.astype(np.float), cmap='gray')
        ax3.imshow(UINT8_WARP(movingImgSmooth, trans), cmap='gray')
        plt.show()

    return Bx, By, angle, fval

def _imgGaussian(img, sigma):
    return np.round(gaussian_filter(img.astype(np.float), sigma)).astype(np.uint8)

def _affineError(par,I1,I2,drawTitle=None):
    trans = centreRotation(I1.shape, R=par[2], T=(par[1], par[0]))
    warpedImg = UINT8_WARP(I1, trans)

    if drawTitle is not None:
        f, (ax1, ax2, ax3) = plt.subplots(1, 3)
        f.suptitle(drawTitle)
        ax1.imshow(I1.astype(np.float), cmap='gray')
        ax2.imshow(I2.astype(np.float), cmap='gray')
        ax3.imshow(warpedImg.astype(np.float), cmap='gray')
        plt.show()

    errorScale = 1 + 0.1 * np.sqrt(par[0] ** 2 + par[1] ** 2)
    imgDelta = _imageDifference(I2, warpedImg)
    fval = imgDelta * errorScale
    return fval

def affine_registration_error_2d(par,I1,I2,type,mode):
    M = _getTransformationMatrix(par)
    I3 = _affineTransform(I1, M, mode)
    e = _imageDifference(I3, I2)

def _getTransformationMatrix(par):
    assert len(par) == 3
    return _makeTransformationMatrix(par[0:2], par[3])

def _makeTransformationMatrix(t, r):
    assert len(t) == 2
    # No scaling, no shear.
    rotatMatrix = np.array([ [np.cos(r), np.sin(r), 0], [-np.sin(r), np.cos(r), 0], [0, 0, 1]])
    transMatrix = np.array([ [1, 0, t[0]], [0, 1, t[1]], [0, 0, 1]])
    return np.matmul(transMatrix, rotatMatrix)

def _imageDifference(fr, to):
    # Squared difference
    delta = (fr.astype(np.int32) - to.astype(np.int32))
    return np.mean(delta ** 2)

def _movePixels(oldVolume, dX, dY, dZ):
    assert oldVolume.shape == dX.shape and oldVolume.shape == dY.shape and oldVolume.shape == dZ.shape
    (nx, ny, nz) = oldVolume.shape
    newVolume = np.zeros(oldVolume.shape)

    for i in range(nx):
        for j in range(ny):
            for k in range(nz):
                # TODO: bilinear interpolation
                x = i + int(round(dX[i, j, k]))
                y = j + int(round(dY[i, j, k]))
                z = k + int(round(dZ[i, j, k]))
                if 0 <= x and x < nx and 0 <= y and y < ny and 0 <= z and z < nz:
                    newVolume[i, j, k] = oldVolume[x, y, z]

    return newVolume
