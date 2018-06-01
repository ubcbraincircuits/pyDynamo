import libtiff
import numpy as np

from tifffile import TiffFile

# HACK
import matplotlib.pyplot as plt

libtiff.libtiff_ctypes.suppress_warnings()

def asMatrix(asList, nRows):
    nCols = int(len(asList) / nRows)
    assert nRows * nCols == len(asList), "List wrong size for matrix conversion"
    return [asList[i:i+nCols] for i in range(0, len(asList), nCols)]

def tiffRead(path, useLibTiff=False):
    # First use tifffile to get channel data (not supported by libtiff?)
    shape = None
    stack = None
    with TiffFile(path) as tif:
        shape = tif.asarray().shape
        stack = tif.asarray()
    nChannels = shape[0] if len(shape) == 4 else 1
    print ("TIF shape: ")
    print (shape)


    if useLibTiff:
        stack = []
        tif = libtiff.TIFF.open(path, mode='r')
        stack = asMatrix([np.array(img) for img in tif.iter_images()], nChannels)
        tif.close()
    else:
        if len(shape) == 3:
            stack = np.expand_dims(stack, axis=0)

    mx = np.max(np.array(stack))
    stack = [(img / mx).astype(np.float16) for img in stack]

    ## MEGA HACK
    # stack = np.array(stack)
    # stack = np.swapaxes(stack, 0, 1)
    # stack = list(stack)
    return stack
