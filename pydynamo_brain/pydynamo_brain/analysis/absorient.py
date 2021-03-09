import math
import numpy as np

# http://nghiaho.com/?page_id=671

from typing import Any, List, Tuple

from pydynamo_brain.util import Point3D

# TODO: scaling?
def absOrient(
    pointsFrom: List[Point3D], pointsTo: List[Point3D]
) -> Tuple[List[Tuple[Any, ...]], np.ndarray, np.ndarray]:
    """Minimize ||R*pointsFrom + T - pointsTo||

    pointsFrom: list( tuple(x, y, z) )
    pointsTo: list( tuple(x, y, z) )
    """

    assert len(pointsFrom) == len(pointsTo), "absorient inputs must be same length"
    nPoints = len(pointsFrom)

    npFrom, npTo = np.array(pointsFrom), np.array(pointsTo)
    midFrom, midTo = np.mean(npFrom, axis=0), np.mean(npTo, axis=0)
    left, right = npFrom - midFrom, npTo - midTo

    # HACK - what is M?
    M = np.matmul(left.T, right) # 3x3
    Sxx,Syx,Szx,Sxy,Syy,Szy,Sxz,Syz,Szz = tuple(M.T.flatten())
    N = np.array([
        [Sxx+Syy+Szz,     Syz-Szy,      Szx-Sxz,      Sxy-Syx],
        [    Syz-Szy, Sxx-Syy-Szz,      Sxy+Syx,      Szx+Sxz],
        [    Szx-Sxz,     Sxy+Syx, -Sxx+Syy-Szz,      Syz+Szy],
        [    Sxy-Syx,     Szx+Sxz,      Syz+Szy, -Sxx-Syy+Szz]
    ])

    # V = vectors, D = diag(values)
    eigVal, eigVec = np.linalg.eig(N)
    eigMaxIdx = np.argmax(np.real(eigVal))
    eigVal = np.diag(eigVal)
    q = np.real(eigVec[:, eigMaxIdx])

    qMax = np.argmax(np.abs(q))
    # Sign ambiguity
    q = q * np.sign(q[qMax])
    R = quatern2orth(q)

    T = midTo - np.matmul(R, midFrom)
    fitTo = np.matmul(npFrom, R.T) + T
    fitAsTuples = [tuple(row) for row in fitTo]
    return fitAsTuples, R, T

def quatern2orth(quat: np.ndarray) -> np.ndarray:
    """
    Map a quaternion to an orthonormal 3D matrix
     R=quatern2orth(quat)
    in:
     quat: A quaternion [q0 qx qy qz]'
    out:
     R: The orthonormal 3D matrix induced by the
        unit quaternion quat/norm(quat)
    """
    nrm = np.linalg.norm(quat)
    assert nrm > 0, "Singular quaternion :("
    quat = quat / nrm
    q0, qx, qy, qz = tuple(quat)
    v = np.array([qx, qy, qz])

    A = np.array([
        [ q0, -qz,  qy],
        [ qz,  q0, -qx],
        [-qy,  qx,  q0]
    ])
    return np.outer(v, v) + np.matmul(A, A)
