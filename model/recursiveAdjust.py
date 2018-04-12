import util

def recursiveAdjust(id, branch, point, pointref, Rxy=30, Rz=4):
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
    oldBox = _imageBoxIfInside(volume, oldLocMin, oldLocMax)
    if oldBox is None:
        # hilight this point
        recursiveHighlight(branch, fromPointIdx=point.indexInParent())
        return


    xyz = point.location # round(state{id}.tree{branch}{1}(:, point));
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
    newBox = _imageBoxIfInside(volume, newLocMin, newLocMax)
    if newBox is None:
        recursiveHighlight(branch, fromPointIdx=point.indexInParent())

    # align the z-projected images in XY
    # [Bx,By, angle, fval] = register_images2(max(oldbox,[], 3),max(newbox,[], 3),Options);
    opt = {
        'Similarity': 'p',
        'Registration': 'Rigid',
        'Verbose': 0,
    }
    Bx, By, angle, fval = registerImages(np.max(oldBox, axis=2), np.max(newBox, axis=2), opt)

    I1 = np.mean(np.power(oldBox, 2))
    I2 = np.mean(np.power(newBox, 2))
    # I1 = mean(oldbox(:).^2);
    # I2 = mean(newbox(:).^2);

    # the alignment is poor; give up!
    if abs(angle)>0.3 or isempty(fval) or fval > (max(I1,I2)*0.9) or abs(Bx(Rxy+1,Rxy+1))>(Rxy*0.8) or abs(By(Rxy+1,Rxy+1))>(Rxy*0.8):
        if Rxy < 25: # try a larger window
            recursiveAdjust(id, branch, point, pointref, 25, 4)
        else:
            recursiveHighlight(branch, fromPointIdx=point.indexInParent())
            # state{id}.tree{branch}{4}(point:size(state{id}.tree{branch}{1},2)) = 1; %highlight this point
            # j = cell2mat(state{id}.tree{branch}{2}(point:end));
            # recursivehighlight(j, id);
        return

    # Find optimal Z-offset for known 2d alignment
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
    nextPoint = point.nextPointInBranch()
    nextPointRef = pointref.nextPointInBranch()
    if nextPoint is not None and nextPointRef is not None:
        deltaXYZ = np.abs(util.locationMinus(nextPoint.location, point.location))
        dXY = np.round(util.snapToRange(np.max(deltaXYZ[0:1]), 20, 30))
        dZ = np.round(util.snapToRange(deltaXYZ[2], 2, 4) + 1)
        recursiveAdjust(id, branch, nextPoint, nextPointRef, dXY, dZ)



    # for child = state{id}.tree{branch}{2}{point}
        # recursiveadjust(id, child, 2, 2);
    for branch in point.children:
        HACK = None # Load corresponding old point
        recursiveAdjust(id, branch, branch.points[0], HACK)


def _recursiveMoveBranch(branch, shift, fromPointIdx=0):
    for pointToMove in branch.points[fromPointIdx]:
        pointToMove.location = util.locationPlus(pointToMove.location, shift)
        for childBranch in pointToMove.children:
            _recursiveMoveBranch(childBranch, shift)

def _recursiveHilight(branch, fromPointIdx=0):
    for pointToHilight in branch.points[fromPointIdx:]:
        pointToHilight.hilighted = True
        for childBranch in pointToMove.children:
            _recursiveHilight(childBranch)

def _imageBoxIfInside(volume, fr, to):
    to = util.locationPlus(to, (1, 1, 1)) # inclusive to exclusive upper bounds
    for d in range(3): # Verify the box fits inside the volume:
        if fr[d] < 0 or to[d] > volume.size[d]:
            return None
    return volume[fr[0]:to[0], fr[1]:to[1], fr[2]:to[2]]

def _registerImages():
    # TODO
    """
    Inputs,
%   Imoving : The image which will be registerd
%   Istatic : The image on which Imoving will be registered
%   Options : Registration options, see help below
%
% Outputs,
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
    return None

def _imageDifference():
    # TODO
    return None

def _movePixels():
    # TODO
    return None
