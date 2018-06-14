import numpy as np
import util

import matplotlib.pyplot as plt

import scipy.optimize
from scipy.ndimage.filters import gaussian_filter

from skimage import transform as tf

WARP_MODE = 'edge'

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
    print (pointref.location)
    print (point.location)

    # TO DO:
    # subsample images for speed?

    # Options.Similarity = 'p';
    # Options.Registration = 'Rigid';
    # Options.Verbose = 0;

    # extract the 'boxes'; subimages for alignment
    xyz = pointref.location # round(state{id-1}.tree{branch}{1}(:, pointref));
    print ("Point location", xyz)
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
    print ("Making old box...")
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
    print ("Making new box...")
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
    print ("XY transform fitting")
    print ("Means: %f - %f" % (np.mean(newBox), np.mean(oldBox)))
    Bx, By, angle, fval = _registerImages(np.max(oldBox, axis=2), np.max(newBox, axis=2), opt)
    I1 = np.mean(oldBox ** 2)
    I2 = np.mean(newBox ** 2)
    if True or (id == 1 and point.id == "00000000"):
        print (id)
        print (point.id)
        print ("----------")
        print ("Register result:")
        # print (Bx, By, angle, fval)
        print ('A : %f - F : %f' % (angle, fval))
        print ('I1: %f - I2: %f' % (I1, I2))
        print ("----------")
        return


    # I1 = mean(oldbox(:).^2);
    # I2 = mean(newbox(:).^2);

    # the alignment is poor; give up!
    fTooBad = (fval is None) or fval > (np.max(I1,I2)*0.9)
    xMoveTooFar = np.abs(Bx[Rxy+1,Rxy+1]) > (Rxy*0.8)
    yMoveTooFar = np.abs(By[Rxy+1,Rxy+1]) > (Rxy*0.8)
    if (np.abs(angle) > 0.3 or fTooBad or xMoveTooFar or yMoveTooFar):
        print ("Bad fit! larger window if %d < 25" % Rxy)
        if Rxy < 25: # try a larger window
            recursiveAdjust(id, branch, point, pointref, 25, 4)
        else:
            _recursiveHilight(branch, fromPointIdx=point.indexInParent())
            # state{id}.tree{branch}{4}(point:size(state{id}.tree{branch}{1},2)) = 1; %highlight this point
            # j = cell2mat(state{id}.tree{branch}{2}(point:end));
            # recursivehighlight(j, id);
        return

    # Find optimal Z-offset for known 2d alignment
    print ("Z transform fitting")

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

    # find optimum
    minIdx = np.argmin(score)
    minVal = score[minIdx]
    # [minVal minIx] = np.min(score);

    shiftX = -By[Rxy+1, Rxy+1]
    shiftY = -Bx[Rxy+1, Rxy+1]
    shiftZ = minIdx - Rz - 1
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
        dXY = np.round(util.snapToRange(np.max(deltaXYZ[0:1]), 20, 30))
        dZ = np.round(util.snapToRange(deltaXYZ[2], 2, 4) + 1)
        recursiveAdjust(id, branch, nextPoint, nextPointRef, dXY, dZ)

    # for child = state{id}.tree{branch}{2}{point}
        # recursiveadjust(id, child, 2, 2);
    print ("Adjusting children...")
    for branch in point.children:
        HACK = None # Load corresponding old point
        recursiveAdjust(id, branch, branch.points[0], HACK)
    print ("Done!")

def _recursiveMoveBranch(branch, shift, fromPointIdx=0):
    for pointToMove in branch.points[fromPointIdx]:
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
    print ("IBiI")
    print (fr)
    print (to)
    print ("MEAN VOL = ")
    print (np.mean(volume))
    to = util.locationPlus(to, (1, 1, 1)) # inclusive to exclusive upper bounds
    s = volume.shape # (channels, stacks, x, y)
    volumeXYZ = (s[2], s[3], s[1])
    for d in range(3): # Verify the box fits inside the volume:
        if fr[d] < 0 or volumeXYZ[d] < to[d]:
            return None
    subVolume = volume[channel, fr[2]:to[2], fr[1]:to[1], fr[0]:to[0]] # ZYX
    subVolume = np.moveaxis(subVolume, 0, -1) # YXZ
    # subVolume = np.swapaxes(subVolume, 0, 2) # XYZ
    print ("SVS", subVolume.shape)
    print ("MEAN SUBVOL = ")
    print (np.mean(subVolume))
    return subVolume

def _registerImages(movingImg, staticImg, opt):
    # TODO
    """
    Inputs,
%   Imoving : The image which will be registerd
%   Istatic : The image on which Imoving will be registered
%   Options : Registration options, see help below
%
% Outputs,

%   Bx, By : The backwards transformation fields of the pixels in
%       x and y direction seen from the  static image to the moving image.
%   angle : rotation (?) in shift
%   fVal : Error in final transform.

%   Ireg : The registered moving image
%   Bx, By : The backwards transformation fields of the pixels in
%       x and y direction seen from the  static image to the moving image.
%   Fx, Fy : The (approximated) forward transformation fields of the pixels in
%       x and y direction seen from the moving image to the static image.
%       (See the function backwards2forwards)
% Options,
%   Options.SigmaFluid : The sigma of the gaussian smoothing kernel of the pixel
%                   velocity field / update field, this is a form of fluid
%                   regularization, (default 4)
%   Options.SigmaDiff : The sigma for smoothing the transformation field
%                   is not part of the orignal demon registration, this is
%                   a form of diffusion regularization, (default 1)
%   Options.Interpolation : Linear (default) or Cubic.
%   Options.Alpha : Constant which reduces the influence of edges (and noise)
%                   and limits the update speed (default 4).
%   Options.Similarity : Choose 'p' for single modality and 'm' for
%                   images of different modalities. (default autodetect)
%   Options.Registration: Rigid, Affine, NonRigid
%   Options.MaxRef : Maximum number of grid refinements steps.
%   Options.Verbose: Display Debug information 0,1 or 2
    """


    # % Disable warning
    # warning('off', 'MATLAB:maxNumCompThreads:Deprecated')

    # % Process inputs
    # defaultoptions=struct('Similarity',[],'Registration','NonRigid','MaxRef',[],'Verbose',2,'SigmaFluid',4,'Alpha',4,'SigmaDiff',1,'Interpolation','Linear');
    # if(~exist('Options','var')),
        # Options=defaultoptions;
    # else
        # tags = fieldnames(defaultoptions);
        # for i=1:length(tags)
            #  if(~isfield(Options,tags{i})),  Options.(tags{i})=defaultoptions.(tags{i}); end
        # end
        # if(length(tags)~=length(fieldnames(Options))),
            # warning('register_images:unknownoption','unknown options found');
        # end
    # end

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
    x=[0, 0, 0]

    # for refine_itt=1:1   # WAT?!?!
        # if(refine_itt==2)
            # ISmoving=Imoving; ISstatic=Istatic;
        # end
    if False:              # WAT?!?!
        movingImgSmooth, staticImgSmooth = movingImg, staticImg


    def _affineRegistrationError(x):
        return _affineError(x, scale, movingImgSmooth, staticImgSmooth, type='sd', mode=0)

    """
    	% Use struct because expanded optimset is part of the Optimization Toolbox.
        %optim=struct('GradObj','off','Display','off','MaxIter',80,'MaxFunEvals',800,'TolFun',1e-6,'DiffMinChange',1e-6);
        optim=struct('GradObj','off','GoalsExactAchieve',1,'Display','off','MaxIter',100,'MaxFunEvals',1000,'TolFun',1e-10,'DiffMinChange',1e-6);
    	%optim=struct('GradObj','off','GoalsExactAchieve',1,'Display','off','MaxIter',100,'MaxFunEvals',1000,'TolFun',1e-14,'DiffMinChange',1e-6);
        %[x, fval]=fminunc(@(x)affine_registration_error(x,scale,ISmoving,ISstatic,type_affine),x,optim);
        [x, fval]=fminlbfgs(@(x)(affine_registration_error(x,scale,ISmoving,ISstatic,type_affine)*(1+ 0.1*sqrt(sum(x(1:2).^2)))),x,optim);
    end
    """
    res = scipy.optimize.minimize(_affineRegistrationError, x, method='L-BFGS-B')
    if not res.success:
        print (res.message)
        raise ("COULD NOT OPTIMIZE!")
    x = res.x
    print ("BEST:")
    print (x)

    trans = tf.AffineTransform(rotation=x[2], translation=(x[0], x[1]))
    # M = trans.matrix
    M = _makeTransformationMatrix((x[0], x[1]), x[2])
    warpedImgSmooth = tf.warp(movingImgSmooth, trans, mode=WARP_MODE)

    # [x,y]=ndgrid(0:(movingImg.shape[0]-1),0:(movingImg.shape[1]-1));
    x, y = np.meshgrid(range(movingImg.shape[0]), range(movingImg.shape[1]))
    xd = x - (movingImg.shape[0]/2)
    yd = y - (movingImg.shape[1]/2)
    Bx = ((movingImg.shape[0]/2) + M[0, 0] * xd + M[0, 1] * yd + M[0, 2] * 1) - x;
    By = ((movingImg.shape[1]/2) + M[1, 0] * xd + M[1, 1] * yd + M[1, 2] * 1) - y;
    angle = trans.rotation

    f, (ax1, ax2, ax3) = plt.subplots(1, 3)
    print ("SHOWING")
    print(np.min(movingImg.astype(np.float)), np.max(movingImg.astype(np.float)))
    ax1.imshow(movingImgSmooth.astype(np.float), cmap='gray')
    ax2.imshow(staticImgSmooth.astype(np.float), cmap='gray')
    ax3.imshow(tf.warp(movingImgSmooth.astype(np.float), trans, mode=WARP_MODE), cmap='gray')
    plt.show()

    fval = _imageDifference(staticImgSmooth, warpedImgSmooth)
    return Bx, By, angle, fval

    """

    # % Make the rigid transformation matrix
    M=make_transformation_matrix(x(1:2),x(3));
    angle = x(3);

    # % Make center of the image transformation coordinates 0,0
    [x,y]=ndgrid(0:(size(Imoving,1)-1),0:(size(Imoving,2)-1));
    xd=x-(size(Imoving,1)/2); yd=y-(size(Imoving,2)/2);

    # % Calculate the backwards transformation fields
    Bx = ((size(Imoving,1)/2) + M(1,1) * xd + M(1,2) *yd + M(1,3) * 1)-x;
    By = ((size(Imoving,2)/2) + M(2,1) * xd + M(2,2) *yd + M(2,3) * 1)-y;

    return None
    ""
    trans = tf.AffineTransform()
    print ("Fr: %s" % str(movingImg.shape))
    print ("To: %s" % str(staticImg.shape))
    trans.estimate(movingImg, staticImg)
    warpedImg = tf.warp(movingImg, trans, mode=WARP_MODE)

    M = trans.matrix

    # [x,y]=ndgrid(0:(movingImg.shape[0]-1),0:(movingImg.shape[1]-1));
    x, y = np.meshgrid(range(movingImg.shape[0]), range(movingImg.shape[1]))
    xd = x - (movingImg.shape[0]/2)
    yd = y - (movingImg.shape[1]/2)
    Bx = ((movingImg.shape[0]/2) + M[0, 0] * xd + M[0, 1] * yd + M[0, 2] * 1) - x;
    By = ((movingImg.shape[1]/2) + M[1, 0] * xd + M[1, 1] * yd + M[1, 2] * 1) - y;
    angle = trans.rotation

    errorScale = 1 + 0.1 * np.sqrt(trans.translation[0] ** 2 + trans.translation[1] ** 2)
    fval = _imageDifference(staticImg, warpedImg) * (errorScale) # TODO - error scale during estimate?
    return Bx, By, angle, fval
    """

def _imgGaussian(img, sigma):
    return gaussian_filter(img.astype(np.float), sigma)

def _affineError(par,scale,I1,I2,type,mode):
    """
    % This function affine_registration_error, uses affine transfomation of the
    % 3D input volume and calculates the registration error after transformation.
    %
    % [e,egrad]=affine_registration_error(parameters,scale,I1,I2,type,Grid,Spacing,MaskI1,MaskI2,Points1,Points2,PStrength,mode);
    %
    % input,
    %   parameters (in 2D) : Rigid vector of length 3 -> [translateX translateY rotate]
    %                        or Affine vector of length 7 -> [translateX translateY
    %                                           rotate resizeX resizeY shearXY
    %                                           shearYX]
    %
    %   parameters (in 3D) : Rigid vector of length 6 : [translateX translateY translateZ
    %                                           rotateX rotateY rotateZ]
    %                       or Affine vector of length 15 : [translateX translateY translateZ,
    %                             rotateX rotateY rotateZ resizeX resizeY
    %                             resizeZ,
    %                             shearXY, shearXZ, shearYX, shearYZ, shearZX, shearZY]
    %
    %   scale: Vector with Scaling of the input parameters with the same lenght
    %               as the parameter vector.
    %   I1: The 2D/3D image which is rigid or affine transformed
    %   I2: The second 2D/3D image which is used to calculate the
    %       registration error
    %   type: The type of registration error used see registration_error.m
    % (optional)
    %   mode: If 0: linear interpolation and outside pixels set to nearest pixel
    %            1: linear interpolation and outside pixels set to zero
    %            2: cubic interpolation and outsite pixels set to nearest pixel
    %            3: cubic interpolation and outside pixels set to zero
    %
    % outputs,
    %   e: registration error between I1 and I2
    %   egrad: error gradient of input parameters
    % example,
    %   see example_3d_affine.m
    %
    % Function is written by D.Kroon University of Twente (April 2009)
    """

    # % Scale the inputs
    # par=par.*scale;
    assert scale == [1, 1, 1] # TODO - remove scale

    # % Delta
    delta = 1e-5

    # Special case for simple squared difference (speed optimized code)
    # if((size(I1,3)>3)&&(strcmp(type,'sd')))
        # ... never used, as we're only passing 2D images


    """
    % Normal error calculation between the two images, and error gradient if needed
    % by final differences
    if(size(I1,3)<4)
        e=affine_registration_error_2d(par,I1,I2,type,mode);
        if(nargout>1)
            egrad=zeros(1,length(par));
            for i=1:length(par)
                par2=par; par2(i)=par(i)+delta*scale(i);
                egrad(i)=(affine_registration_error_2d(par2,I1,I2,type,mode)-e)/delta;
            end
        end
    """
    # else
        # 3D affine code removed...

    trans = tf.AffineTransform(rotation=par[2], translation=(par[0], par[1]))
    warpedImg = tf.warp(I1, trans, mode=WARP_MODE)

    errorScale = 1 # + 0.1 * np.sqrt(par[0] ** 2 + par[1] ** 2)
    fval = _imageDifference(I2, warpedImg) * (errorScale)
    return fval


def affine_registration_error_2d(par,I1,I2,type,mode):
    # function e=affine_registration_error_2d(par,I1,I2,type,mode)
    # M=getransformation_matrix(par);
    # I3=affine_transform(I1,M,mode);

    # % registration error calculation.
    # e = image_difference(I3,I2,type);
    M = _getTransformationMatrix(par)
    I3 = _affineTransform(I1, M, mode)
    e = _imageDifference(I3, I2, type)

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
    return np.mean((fr - to) ** 2)

def _movePixels():
    # TODO
    return None
