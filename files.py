import libtiff

libtiff.libtiff_ctypes.suppress_warnings()

def tiffRead(path):
    tif = libtiff.TIFF.open(path, mode='r')
    stack = [img for img in tif.iter_images()]
    tif.close()
    return stack
