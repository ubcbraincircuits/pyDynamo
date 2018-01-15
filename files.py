from libtiff import TIFF

def tiffRead(path):
    tif = TIFF.open(path, mode='r')
    stack = [img for img in tif.iter_images()]
    tif.close()
    return stack
