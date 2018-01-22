# https://github.com/hmeine/qimage2ndarray

from PyQt5.QtGui import QImage, qRgb

import numpy as np

def PyQt_data(image):
    # PyQt4/PyQt5's QImage.bits() returns a sip.voidptr that supports
    # conversion to string via asstring(size) or getting its base
    # address via int(...):
    return

def qimageview(image):
    image.__array_interface__ = {
        'shape': (image.height(), image.width()),
        'typestr': "|u1",
        'data': (int(image.bits()), False),
        'strides': (image.bytesPerLine(), 1),
        'version': 3,
    }

    result = np.asarray(image)
    del image.__array_interface__
    return result

def _normalize255(array, normalize, clip = (0, 255)):
    if normalize:
        if normalize is True:
            normalize = array.min(), array.max()
            if clip == (0, 255):
                clip = None
        elif np.isscalar(normalize):
            normalize = (0, normalize)

        nmin, nmax = normalize

        if nmin:
            array = array - nmin

        if nmax != nmin:
            scale = 255. / (nmax - nmin)
            if scale != 1.0:
                array = array * scale

    if clip:
        low, high = clip
        np.clip(array, low, high, array)

    return array

def np2qt(gray, normalize = False):
    """Convert the 2D numpy array `gray` into a 8-bit, indexed QImage_
    with a gray colormap.  The first dimension represents the vertical
    image axis.
    The parameter `normalize` can be used to normalize an image's
    value range to 0..255:
    `normalize` = (nmin, nmax):
      scale & clip image values from nmin..nmax to 0..255
    `normalize` = nmax:
      lets nmin default to zero, i.e. scale & clip the range 0..nmax
      to 0..255
    `normalize` = True:
      scale image values to 0..255 (same as passing (gray.min(),
      gray.max()))
    If the source array `gray` contains masked values, the result will
    have only 255 shades of gray, and one color map entry will be used
    to make the corresponding pixels transparent.
    """
    if np.ndim(gray) != 2:
        raise ValueError("gray2QImage can only convert 2D arrays" +
                         " (try using array2qimage)" if np.ndim(gray) == 3 else "")

    h, w = gray.shape
    result = QImage(w, h, QImage.Format_Indexed8)

    if not np.ma.is_masked(gray):
        for i in range(256):
            result.setColor(i, qRgb(i,i,i))
        qimageview(result)[:] = _normalize255(gray, normalize)
    return result
