import numpy as np

from analysis import absOrient

def matchPoints(A, B):
    if len(A) != len(B):
        return False
    for a, b in zip(A, B):
        if not np.isclose(np.array(a), np.array(b)).all():
            return False
    return True

def testAbsOrient():
    pointsFrom = [(1, 0, 0), (0, 1, 0), (0, 0, 1)]
    fitTo, R, T = absOrient(pointsFrom, pointsFrom)
    assert matchPoints(fitTo, pointsFrom)
    assert np.allclose(R, np.eye(3))
    assert np.allclose(T, np.zeros((1, 3)))

    pointsTo = [(1, 1, 0), (0, 1, 1), (0, 0, 0)]
    fitTo, R, T = absOrient(pointsFrom, pointsTo)
    assert matchPoints(fitTo, pointsTo)
    assert np.allclose(R, np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]]))
    assert np.allclose(T, np.array([0, 1, 0]))

    pointsFrom = [(1, 2, 3), (4, 5, 6), (3, 2, 1), (1, 0, 1), (1, 1, -5)]
    pointsTo = [(3, 2, 1), (4, -4, 4), (2, 3, 1), (0, 0, 8), (1, 2, -5)]
    fitTo, R, T = absOrient(pointsFrom, pointsTo)

    shouldFit = np.array([
        (2.945034854502740,  0.928946312821941,  3.599639810366461),
        (4.825051621265003, -3.763165577948376,  4.803642701220368),
        (1.472862022944265, -0.207709337018714,  1.468743030204076),
        (0.741888608578181,  2.321911476582198,  2.501552987014645),
        (0.015162892709808,  3.720017125562951, -3.373578528805551)
    ])
    shouldR = np.array([
        [-0.47490087,  0.84038757,  0.26118555],
        [-0.86755472, -0.39725569, -0.29922689],
        [-0.14770911, -0.36869586,  0.91773928]
    ])
    shouldT = np.array([[0.95560393, 3.48869308, 1.73152283]])
    assert matchPoints(fitTo, shouldFit)
    assert np.allclose(R, shouldR)
    assert np.allclose(T, shouldT)
    print ("Abs Orient passed! 🙌")

def run():
    np.set_printoptions(precision=4, suppress=True)
    testAbsOrient()
    np.set_printoptions()
    return True

if __name__ == '__main__':
    run()
