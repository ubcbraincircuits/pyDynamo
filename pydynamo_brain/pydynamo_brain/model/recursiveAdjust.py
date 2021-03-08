import numpy as np
import matplotlib.pyplot as plt
import scipy.optimize
from scipy.ndimage.filters import gaussian_filter
from skimage import transform as tf

import pydynamo_brain.util as util

WARP_MODE = 'edge'

_IMG_CACHE = util.ImageCache()

def centreRotation(shape, T, R):
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

def recursiveAdjust(fullState, id, branch, point, pointref, callback, Rxy=10, Rz=4):
    """
    recursively adjusts points, i.e. the 'R' function
    id       -image on which to adjust (reference is id-1)
    branch   -the branch being adjusted
    point    -point in id being adjusted
    pointref -point in id-1 being adjusted
    callback -called for progress updates

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
    oldBox = _imageBoxIfInsideXY(volume, fullState.channel, oldLocMin, oldLocMax)
    if oldBox is None:
        callback(_recursiveMark(newTree, branch, fromPointIdx=point.indexInParent()))
        return

    xyz = point.location
    xyz = (int(np.round(xyz[0])), int(np.round(xyz[1])), int(np.round(xyz[2])))
    newLocMin = util.locationMinus(xyz, dLoc)
    newLocMax = util.locationPlus(xyz, dLoc)
    volume = _IMG_CACHE.getVolume(fullState.uiStates[id].imagePath)
    newBox = _imageBoxIfInsideXY(volume, fullState.channel, newLocMin, newLocMax)
    if newBox is None:
        callback(_recursiveMark(newTree, branch, fromPointIdx=point.indexInParent()))
        return

    I1 = np.mean(oldBox.astype(np.int32) ** 2)
    I2 = np.mean(newBox.astype(np.int32) ** 2)

    # align the z-projected images in XY
    drawTitle = None
    # if point.id == "000001aa":
        # drawTitle = point.id
    Bx, By, angle, fval = _registerImages(np.max(oldBox, axis=2), np.max(newBox, axis=2), Rxy, drawTitle=drawTitle)

    # the alignment is poor; give up!
    fTooBad = (fval is None) or fval > (max(I1,I2) * 1.5)
    angleTooFar, xMoveTooFar, yMoveTooFar = True, True, True
    print ("Registering %s...\t" % (point.id), end='')
    if fval is not None:
        xMoveTooFar = np.abs(Bx[Rxy+1,Rxy+1]) > (Rxy*0.8)
        yMoveTooFar = np.abs(By[Rxy+1,Rxy+1]) > (Rxy*0.8)
        angleTooFar = np.abs(angle) > 0.3

    if (fTooBad or angleTooFar or xMoveTooFar or yMoveTooFar):
        print ("bad fit! larger window if %d < 25" % Rxy)
        if Rxy < 25: # try a larger window
            recursiveAdjust(fullState, id, branch, point, pointref, callback, 25, 4)
        else:
            callback(_recursiveMark(newTree, branch, fromPointIdx=point.indexInParent()))
        return

    # Find optimal Z-offset for known 2d alignment
    mX, mY, mZ = np.dstack([Bx] * (2*Rz + 1)), np.dstack([By] * (2*Rz + 1)), np.zeros(oldBox.shape)
    oldBoxShifted = _movePixels(oldBox, mX, mY, mZ)

    bestZ, bestZScore = None, 0
    for dZ in range(-Rz, Rz + 1):
        xyNewZ = (xyz[0], xyz[1], xyz[2] + dZ)
        newLocMinZ = util.locationMinus(xyNewZ, dLoc)
        newLocMaxZ = util.locationPlus(xyNewZ, dLoc)
        newBoxZ = _imageBoxIfInsideXY(volume, fullState.channel, newLocMinZ, newLocMaxZ)
        if newBoxZ is None:
            continue
        delta = _imageDifference(oldBoxShifted, newBoxZ)
        score = delta * (6 + abs(dZ) ** 1.1)
        if bestZ is None or bestZScore > score:
            bestZ, bestZScore = dZ, score

    shiftX = Bx[Rxy, Rxy]
    shiftY = By[Rxy, Rxy]
    shiftZ = bestZ # minIdx - Rz - 1
    shift = (shiftX, shiftY, shiftZ)
    print ("moving by (%.3f, %.3f, %.3f)" % (shiftX, shiftY, shiftZ))

    # Point successfully registered to Pointref!
    fullState.setPointIDWithoutCollision(newTree, point, pointref.id)
    callback(1)
    if point.indexInParent() == 0 and point.parentBranch is not None and pointref.parentBranch is not None:
        fullState.setBranchIDWithoutCollision(
            newTree, point.parentBranch, pointref.parentBranch.id
        )
    _recursiveMoveBranch(newTree, branch, shift, fromPointIdx=point.indexInParent())

    nextPoint = point.nextPointInBranch(noWrap=True)
    nextPointRef = pointref.nextPointInBranch(noWrap=True)
    if nextPoint is not None and nextPointRef is not None:
        deltaXYZ = np.abs(util.locationMinus(nextPoint.location, point.location))
        dXY = int(round(util.snapToRange(np.max(deltaXYZ[0:1]), 10, 30)))
        dZ = int(round(util.snapToRange(deltaXYZ[2], 2, 4) + 1))
        recursiveAdjust(fullState, id, branch, nextPoint, nextPointRef, callback, dXY, dZ)

    # TODO - match up branches more cleverly, not just based on order
    for i, branch in enumerate(point.children):
        if i >= len(pointref.children): # unmatched branch
            callback(_recursiveMark(newTree, branch))
            continue

        branchRef = pointref.children[i]
        if len(branch.points) == 0:
            continue # empty branch, skip
        elif len(branchRef.points) == 0:
            callback(_recursiveMark(newTree, branch)) # can't match to empty branch
        else:
            recursiveAdjust(fullState, id, branch, branch.points[0], branchRef.points[0], callback)


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

# Mark all down-tree points (mark as un-registered), and return the number marked
def _recursiveMark(tree, branch, fromPointIdx=0):
    nMarked = 0
    if branch is None:
        points = tree.flattenPoints()
        for point in points:
            point.manuallyMarked = True
        nMarked = len(points)
    else:
        for pointToMark in branch.points[fromPointIdx:]:
            pointToMark.manuallyMarked = True
            nMarked = 1
            for childBranch in pointToMark.children:
                nMarked += _recursiveMark(tree, childBranch)
    return nMarked

# Get a subvolume if inside the bigger volume.
# Note that only Z is padded with zeros, XY must fit entirely within.
def _imageBoxIfInsideXY(volume, channel, fr, to):
    to = util.locationPlus(to, (1, 1, 1)) # inclusive to exclusive upper bounds
    s = volume.shape # (channels, stacks, x, y)
    volumeXYZ = (s[2], s[3], s[1])

    for d in range(2): # Verify the XY box fits inside the volume:
        if fr[d] < 0 or volumeXYZ[d] < to[d]:
            return None

    # Figure out how much Z padding is needed...
    addStart, addEnd = 0, 0
    if fr[2] < 0:
        addStart = 0 - fr[2]
        fr = (fr[0], fr[1], 0)
    if volumeXYZ[2] < to[2]:
        addEnd = to[2] - volumeXYZ[2]
        to = (to[0], to[1], volumeXYZ[2])

    subVolume = volume[channel, fr[2]:to[2], fr[1]:to[1], fr[0]:to[0]] # ZYX

    # ...and apply the padding:
    dx, dy = subVolume.shape[1], subVolume.shape[2]
    if addStart > 0:
        subVolume = np.vstack( (np.zeros((addStart, dy, dx)), subVolume) )
    if addEnd > 0:
        subVolume = np.vstack( (subVolume, np.zeros((addEnd, dy, dx))) )

    subVolume = np.moveaxis(subVolume, 0, -1) # YXZ
    return subVolume


def _dualRangeExp(n, v, exp=2.0):
    # Given a number of items, return samples in [-v, v]
    # exponentially biassed towards the centre
    secondHalf = list(v * (np.arange(0, 1, 2 / n) ** exp))
    firstHalf = [-v for v in secondHalf[::-1]]
    return firstHalf + secondHalf[1:]

def _registerImages(staticImg, movingImg, Rxy, drawTitle=None):
    assert staticImg.shape == movingImg.shape
    # Make smooth images for histogram and fast affine registration
    staticImgSmooth, movingImgSmooth = staticImg, movingImg
    if True: # Flip to register of raw, not smoothed
        staticImgSmooth = _imgGaussian(staticImg, 0.5)
        movingImgSmooth = _imgGaussian(movingImg, 0.5)

    # Set initial affine parameters
    params = [0, 0, 0] # tx, ty, r

    def _affineRegistrationError(params):
        err = _affineError(params, staticImgSmooth, movingImgSmooth)
        return err

    # Old scipy optimzer methods:
    """
    opt = {
        # 'maxiter': 100,
        'maxfun': 1000,
        'ftol': 1e-6,
        #'disp': False,
        'Similarity': 'p',
        'Registration': 'Rigid',
        #'verbose': 1,
        #'disp': True,
    }
    # method = 'L-BFGS-B'
    # method = 'BFGS'
    # method = 'Nelder-Mead'
    # res = scipy.optimize.minimize(_affineRegistrationError, params, tol=1e-4, method=method, options=opt)
    # bounds = [(-Rxy, Rxy), (-Rxy, Rxy), (-np.pi, np.pi)]
    # res = scipy.optimize.shgo(_affineRegistrationError, bounds, options=opt)
    """;

    # NOTE: custom optimizer, neither scipy.optimize.minimize nor shgo
    # seem to produce good results.... :'(
    N = 10
    dxys = _dualRangeExp(N, Rxy)
    drs = _dualRangeExp(N, np.pi / 2)

    bestParams, bestErr = None, None
    for dx in dxys:
        for dy in dxys:
            for r in drs:
                params = [dx, dy, r]
                err = _affineRegistrationError(params)
                if bestErr is None or err < bestErr:
                    bestParams, bestErr = params, err

    params = bestParams # res.x

    trans = centreRotation(staticImgSmooth.shape, T=(params[0], params[1]), R=params[2])
    M = trans.params
    warpedImgSmooth = UINT8_WARP(movingImgSmooth, trans)
    fval = _imageDifference(staticImgSmooth, warpedImgSmooth)
    # TODO: use _affineError(x, movingImgSmooth, staticImgSmooth) to include displacement penalty?

    x, y = np.meshgrid(range(movingImg.shape[0]), range(movingImg.shape[1]))
    xd = x - (movingImg.shape[0]/2)
    yd = y - (movingImg.shape[1]/2)
    M[0, 2] = params[0]
    M[1, 2] = params[1]
    Bx = ((movingImg.shape[0]/2) + M[0, 0] * xd + M[0, 1] * yd + M[0, 2] * 1) - x;
    By = ((movingImg.shape[1]/2) + M[1, 0] * xd + M[1, 1] * yd + M[1, 2] * 1) - y;
    angle = trans.rotation

    if drawTitle is not None:
        title = "Best: %s (score %f)" % (str(params), fval)
        f, (ax1, ax2, ax3) = plt.subplots(1, 3)
        f.suptitle(title)
        img1 = np.copy(staticImgSmooth.astype(np.float))
        img2 = np.copy(movingImgSmooth.astype(np.float))
        img3 = np.copy(UINT8_WARP(movingImgSmooth, trans))
        img1[img1.shape[0] // 2, img1.shape[1] // 2] = 1.0
        img2[img2.shape[0] // 2, img2.shape[1] // 2] = 1.0
        img3[img3.shape[0] // 2, img3.shape[1] // 2] = 255
        ax1.imshow(img1, cmap='gray')
        ax2.imshow(img2, cmap='gray')
        ax3.imshow(img3, cmap='gray')
        ax1.set_title("Reference")
        ax2.set_title("Before")
        ax3.set_title("After")
        plt.show()

    return Bx, By, angle, fval

def _imgGaussian(img, sigma):
    return np.round(gaussian_filter(img.astype(np.float), sigma)).astype(np.uint8)

def _affineError(params, staticImg, movingImg, drawTitle=None):
    trans = centreRotation(movingImg.shape, T=(params[0], params[1]), R=params[2])
    warpedImg = UINT8_WARP(movingImg, trans)

    errorScale = 1 + 0.001 * ((params[0] ** 2 + params[1] ** 2) ** 2)
    imgDelta = _imageDifference(staticImg, warpedImg)
    fval = imgDelta * errorScale

    if drawTitle is not None:
        f, (ax1, ax2, ax3) = plt.subplots(1, 3)
        f.suptitle(drawTitle + " (error: %.4f)" % fval)
        img1 = np.copy(staticImg.astype(np.float))
        img2 = np.copy(movingImg.astype(np.float))
        img3 = np.copy(warpedImg.astype(np.float))
        img1[img1.shape[0] // 2, img1.shape[1] // 2] = 1.0
        img2[img2.shape[0] // 2, img2.shape[1] // 2] = 1.0
        img3[img3.shape[0] // 2, img3.shape[1] // 2] = 1.0
        ax1.imshow(img1, cmap='gray')
        ax2.imshow(img2, cmap='gray')
        ax3.imshow(img3, cmap='gray')
        plt.show()
    return fval


def _getTransformationMatrix(params):
    assert len(params) == 3
    return _makeTransformationMatrix(params[0:2], params[3])

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
