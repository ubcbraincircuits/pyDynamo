import numpy as np
import util

import matplotlib.pyplot as plt

import scipy.optimize
from scipy.ndimage.filters import gaussian_filter

from skimage import transform as tf

WARP_MODE = 'edge'

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

    dLoc = (Rxy, Rxy, Rz)

    print('recadj: %d:%d %s->%s (%d,%d)' % (id, branch.indexInParent(), pointref.id, point.id, Rxy, Rz))
    print(pointref.location)
    print(point.location)

    # TO DO:
    # subsample images for speed?

    # Options.Similarity = 'p';
    # Options.Registration = 'Rigid';
    # Options.Verbose = 0;

    # extract the 'boxes'; subimages for alignment
    xyz = pointref.location # round(state{id-1}.tree{branch}{1}(:, pointref));
    xyz = (int(np.round(xyz[0])), int(np.round(xyz[1])), int(np.round(xyz[2])))
    oldLocMin = util.locationMinus(xyz, dLoc)
    oldLocMax = util.locationPlus(xyz, dLoc)
    # xminold = xyz(1)-Rxy;  xmaxold = xyz(1)+Rxy;
    # yminold = xyz(2)-Rxy;  ymaxold = xyz(2)+Rxy;
    # zminold = xyz(3)-Rz;   zmaxold = xyz(3)+Rz;

    # if any([xminold yminold zminold]<1) || any([xmaxold ymaxold zmaxold]>size(traits.imagestack{id-1}))
    #         state{id}.tree{branch}{4}(point:size(state{id}.tree{branch}{1},2)) = 1; %highlight this point
    #         j = cell2mat(state{id}.tree{branch}{2}(point:end));
    #         recursivehighlight(j, id);
    #         return;
    # end
    # oldbox = double(traits.imagestack{id-1}(yminold:ymaxold, xminold:xmaxold, zminold:zmaxold));
    volume = fullState.uiStates[id - 1].imageVolume
    oldBox = _imageBoxIfInside(volume, fullState.channel, oldLocMin, oldLocMax)
    if oldBox is None:
        # hilight this point
        _recursiveHilight(branch, fromPointIdx=point.indexInParent())
        return


    xyz = point.location # round(state{id}.tree{branch}{1}(:, point));
    xyz = (int(np.round(xyz[0])), int(np.round(xyz[1])), int(np.round(xyz[2])))
    newLocMin = util.locationMinus(xyz, dLoc)
    newLocMax = util.locationPlus(xyz, dLoc)
    # xmin = xyz(1)-Rxy;  xmax = xyz(1)+Rxy;
    # ymin = xyz(2)-Rxy;  ymax = xyz(2)+Rxy;
    # zmin = xyz(3)-Rz;   zmax = xyz(3)+Rz;

    # if any([xmin ymin zmin]<1) || any([xmax ymax zmax]>size(traits.imagestack{id}))
    #         state{id}.tree{branch}{4}(point:size(state{id}.tree{branch}{1},2)) = 1; %highlight this point
    #         j = cell2mat(state{id}.tree{branch}{2}(point:end));
    #         recursivehighlight(j, id);
    #         return;
    # end
    # newbox = double(traits.imagestack{id}(ymin:ymax, xmin:xmax, zmin:zmax));
    volume = fullState.uiStates[id].imageVolume
    newBox = _imageBoxIfInside(volume, fullState.channel, newLocMin, newLocMax)
    if newBox is None:
        _recursiveHilight(branch, fromPointIdx=point.indexInParent())
        return

    # align the z-projected images in XY
    # [Bx,By, angle, fval] = register_images2(max(oldbox,[], 3),max(newbox,[], 3),Options);
    opt = {
        'Similarity': 'p',
        'Registration': 'Rigid',
        'Verbose': 0,
    }
    # print ("XY transform fitting")
    # print ("Means: %f - %f" % (np.mean(newBox), np.mean(oldBox)))
    Bx, By, angle, fval = _registerImages(np.max(oldBox, axis=2), np.max(newBox, axis=2), opt)
    I1 = np.mean(oldBox.astype(np.int32) ** 2)
    I2 = np.mean(newBox.astype(np.int32) ** 2)
    if True or (id == 1 and point.id == "00000000"):
        # print (id)
        # print (point.id)
        print ("----------")
        print ("Register result:")
        # print (Bx, By, angle, fval)
        print ('A : %f - F : %f' % (angle, fval))
        print ('I1: %f - I2: %f' % (I1, I2))
        print ("----------")
        # return


    # I1 = mean(oldbox(:).^2);
    # I2 = mean(newbox(:).^2);

    # the alignment is poor; give up!
    fTooBad = (fval is None) or fval > (max(I1,I2)*0.9)
    xMoveTooFar = np.abs(Bx[Rxy+1,Rxy+1]) > (Rxy*0.8)
    yMoveTooFar = np.abs(By[Rxy+1,Rxy+1]) > (Rxy*0.8)
    if (np.abs(angle) > 0.3 or fTooBad or xMoveTooFar or yMoveTooFar):
        print ("Bad fit! larger window if %d < 25" % Rxy)
        if Rxy < 25: # try a larger window
            recursiveAdjust(fullState, id, branch, point, pointref, 25, 4)
        else:
            _recursiveHilight(branch, fromPointIdx=point.indexInParent())
            # state{id}.tree{branch}{4}(point:size(state{id}.tree{branch}{1},2)) = 1; %highlight this point
            # j = cell2mat(state{id}.tree{branch}{2}(point:end));
            # recursivehighlight(j, id);
        return

    # Find optimal Z-offset for known 2d alignment
    # print ("Z transform fitting")
    mX, mY, mZ = np.dstack([Bx] * (2*Rz + 1)), np.dstack([By] * (2*Rz + 1)), np.zeros(oldBox.shape)
    oldBoxShifted = _movePixels(oldBox, mX, mY, mZ)

    bestZ, bestZScore = None, 0
    for dZ in range(-Rz, Rz + 1):
        zAt = xyz[0] + dZ
        dLocZ = (Rxy, Rxy, Rz + dZ)
        newLocMinZ = util.locationMinus(xyz, dLoc)
        newLocMaxZ = util.locationPlus(xyz, dLoc)
        newBoxZ = _imageBoxIfInside(volume, fullState.channel, newLocMinZ, newLocMaxZ)
        if newBoxZ is None:
            continue
        delta = _imageDifference(oldBoxShifted, newBoxZ)
        score = delta * (6 + abs(dZ) ** 1.1)
        if bestZ is None or bestZScore > score:
            bestZ, bestZScore = dZ, score

    print ("Best Z is %d, delta = %d, score = %f" % (bestZ, xyz[0] + bestZ, bestZScore))

    """
    # TODO
    oldIM = movepixels(oldbox + 1, repmat(Bx, [1,1,2*Rz+1]), repmat(By, [1,1,2*Rz+1]), np.zeros(newbox.shape), 3);
    Mask = oldIM ~= 0;
    score = np.zeros((1, 2*Rz+1));
    for Oz in range(-Rz, Rz):
        if zmin + Oz < 1 or zmax + Oz > size(traits.imagestack{id},3):
            score(Oz+Rz+1) = Inf;
        else:
            newIM = double(traits.imagestack{id}(ymin:ymax, xmin:xmax, (zmin:zmax)+Oz))+1;
            score(Oz+Rz+1) = image_difference(oldIM,newIM,'sd',Mask) * (6 + abs(Oz) ** 1.1);
    """

    # # find optimum
    # minIdx = np.argmin(score)
    # minVal = score[minIdx]
    # # [minVal minIx] = np.min(score);

    shiftX = -By[Rxy+1, Rxy+1]
    shiftY = -Bx[Rxy+1, Rxy+1]
    shiftZ = dZ # minIdx - Rz - 1
    shift = (shiftX, shiftY, shiftZ)
    print ("Recursively moving branch by: %s" % (str(shift)))

    # shiftREP = repmat([shiftX shiftY shiftZ]' , 1, size(state{id}.tree{branch}{1},2)-point+1);
    # shiftREP = np.tile(shift, len(branch.points))
    # state{id}.tree{branch}{1}(:, point:end) = state{id}.tree{branch}{1}(:, point:end) + shiftREP ;
    _recursiveMoveBranch(branch, shift, fromPointIdx=point.indexInParent())
    # for pointToMove in branch.points[point.indexInParent():]:
        # pointToMove.location = util.locationPlus(pointToMove.location, shift)
        # childlist = cell2mat(state{id}.tree{branch}{2}(point:end));
        # move child branches
        # recursivemove (childlist, [shiftX shiftY shiftZ]', id);
        # for childBranch in pointToMove.children:
            # _recursiveMoveBranch(childBranch, shift)
    # if point< length(state{id}.tree{branch}{4}) || ~isempty(state{id}.tree{branch}{2}{point})
        # state{id}.tree{branch}{4}(point) = 0; %alignment successful- don't highlight this point
    # end




    # %recursiveadjust the next point, and any child branches
    # if size(state{id}.tree{branch}{1},2)>point && size(state{id-1}.tree{branch}{1},2)>pointref
        # dXYZ = abs(state{id}.tree{branch}{1}(:,point+1)-state{id}.tree{branch}{1}(:,point));
        # dXY = round(min(30,max(20, max(dXYZ(1:2)))));
        # dZ = round(min(4, max(2, dXYZ(3))+1));
        # recursiveadjust(id, branch, point+1, pointref+1, dXY, dZ);
    # recursiveAdjust the next point, and any child branches
    print ("Adjusting next point...")
    nextPoint = point.nextPointInBranch()
    nextPointRef = pointref.nextPointInBranch()
    if nextPoint is not None and nextPointRef is not None:
        deltaXYZ = np.abs(util.locationMinus(nextPoint.location, point.location))
        dXY = int(round(util.snapToRange(np.max(deltaXYZ[0:1]), 20, 30)))
        dZ = int(round(util.snapToRange(deltaXYZ[2], 2, 4) + 1))
        recursiveAdjust(fullState, id, branch, nextPoint, nextPointRef, dXY, dZ)

    # for child = state{id}.tree{branch}{2}{point}
        # recursiveadjust(id, child, 2, 2);
    print ("Adjusting children...")
    for branch in point.children:
        pass
        # HACK = None # Load corresponding old point
        # recursiveAdjust(fullState, id, branch, branch.points[0], HACK)
    print ("Done!")

def _recursiveMoveBranch(branch, shift, fromPointIdx=0):
    for pointToMove in branch.points[fromPointIdx:]:
        pointToMove.location = util.locationPlus(pointToMove.location, shift)
        for childBranch in pointToMove.children:
            _recursiveMoveBranch(childBranch, shift)

def _recursiveHilight(branch, fromPointIdx=0):
    print ("Hi branch " + branch.id)
    for pointToHilight in branch.points[fromPointIdx:]:
        pointToHilight.hilighted = True
        for childBranch in pointToHilight.children:
            _recursiveHilight(childBranch)

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
    # % Resize the moving image to fit the static image
    # if(sum(size(Istatic)-size(Imoving))~=0)
        # Imoving = imresize(Imoving,size(Istatic),'bicubic');
    # end
    assert movingImg.shape == staticImg.shape

    # % Make smooth images for histogram and fast affine registration
    # ISmoving=imgaussian(Imoving,1.5);
    # ISstatic=imgaussian(Istatic,1.5);
    movingImgSmooth = _imgGaussian(movingImg, 1.5)
    staticImgSmooth = _imgGaussian(staticImg, 1.5)


    # type_affine='sd';
    # % Register the moving image affine to the static image


    # % Parameter scaling of the Translation and Rotation
    scale=[1, 1, 1]
    # % Set initial affine parameters
    # x=[0, 0, 0]
    x = [0.5761, -5.8860, -0.1057]
    # for refine_itt=1:1   # WAT?!?!
        # if(refine_itt==2)
            # ISmoving=Imoving; ISstatic=Istatic;
        # end
    if False:              # WAT?!?!
        movingImgSmooth, staticImgSmooth = movingImg, staticImg


    def _affineRegistrationError(x):
        return _affineError(x, scale, movingImgSmooth, staticImgSmooth)

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
    # print ("BEST:")
    # print (x)

    # trans = tf.AffineTransform(rotation=x[2], translation=(x[0], x[1]))
    trans = centreRotation(staticImgSmooth.shape, R=x[2], T=(x[1], x[0]))
    M = trans.params
    # M = _makeTransformationMatrix((x[0], x[1]), x[2])
    warpedImgSmooth = UINT8_WARP(movingImgSmooth, trans)
    fval = _imageDifference(staticImgSmooth, warpedImgSmooth)

    # [x,y]=ndgrid(0:(movingImg.shape[0]-1),0:(movingImg.shape[1]-1));
    x, y = np.meshgrid(range(movingImg.shape[0]), range(movingImg.shape[1]))
    xd = x - (movingImg.shape[0]/2)
    yd = y - (movingImg.shape[1]/2)
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

def _affineError(par,scale,I1,I2,drawTitle=None):
    # % Scale the inputs
    # par=par.*scale;
    assert scale == [1, 1, 1] # TODO - remove scale

    # % Delta
    delta = 1e-5

    # trans = tf.AffineTransform(rotation=par[2], translation=(par[1], par[0])) #Matlab translation is weird
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
    # print ("%s -> %f (%f * %f)" % (str(par), fval, imgDelta, errorScale))
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
