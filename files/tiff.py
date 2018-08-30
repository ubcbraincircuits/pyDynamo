import numpy as np
from tifffile import TiffFile

# libtiff.libtiff_ctypes.suppress_warnings()

def asMatrix(asList, nRows):
    nCols = int(len(asList) / nRows)
    assert nRows * nCols == len(asList), "List wrong size for matrix conversion"
    return [asList[i:i+nCols] for i in range(0, len(asList), nCols)]

def tiffRead(path):
    # First use tifffile to get channel data (not supported by libtiff?)
    shape, stack = None, None
    with TiffFile(path) as tif:
        shape = tif.asarray().shape
        stack = tif.asarray()
    nChannels = shape[0] if len(shape) == 4 else 1
    print ("TIF shape: %s" % str(shape))

    if len(shape) == 3:
        stack = np.expand_dims(stack, axis=0)
    # stack = np.swapaxes(stack, 1, 2)
    return stack
