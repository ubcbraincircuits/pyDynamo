import numpy as np

from files import tiffRead, ImageCache

from model.recursiveAdjust import _imgGaussian, _affineError, _registerImages

_IMAGE_CACHE = ImageCache()

def test():
    oldImg = _IMAGE_CACHE.getVolume('data/testNeuron/R_Live1-1-2002_03-24-20.tif')
    newImg =  _IMAGE_CACHE.getVolume('data/testNeuron/R_Live1-1-2002_04-06-27.tif')

    oldVolume = oldImg[0, 46:55, 756:817, 128:189] # ZYX
    newVolume = newImg[0, 48:57, 776:837, 120:181] # ZYX
    oldVolume = np.moveaxis(oldVolume, 0, -1) # YXZ
    newVolume = np.moveaxis(newVolume, 0, -1) # YXZ

    print ("mean old: ", np.mean(oldVolume))
    print ("mean new: ", np.mean(newVolume))

    movingImg = np.max(oldVolume, axis=2)
    staticImg = np.max(newVolume, axis=2)

    movingImgSmooth = _imgGaussian(movingImg, 1.5)
    staticImgSmooth = _imgGaussian(staticImg, 1.5)

    # x = [0, 0, 0]
    # _affineError(x, [1, 1, 1], movingImgSmooth, staticImgSmooth, drawTitle=str(x))

    # x = [.5761, -5.8860, -0.1057]
    # _affineError(x, [1, 1, 1], movingImgSmooth, staticImgSmooth, drawTitle=str(x))


    # x = [10, -10, np.pi / 3]
    # x = [-30, 15, 0]
    # _affineError(x, [1, 1, 1], movingImgSmooth, staticImgSmooth, drawTitle=str(x))

    _registerImages(movingImg, staticImg, None) #, drawTitle=True)

def run():
    test()
    return True

if __name__ == '__main__':
    run()
