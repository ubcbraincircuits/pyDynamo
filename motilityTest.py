import numpy as np
import scipy.io

from util import emptyArrayMatrix

from calc import addedSubtractedTransitioned, motility, TDBL
from files import importFromMatlab

PROPERTIES = ['added', 'filolengths', 'tdbl', 'masterChanged', 'transitioned', 'masterNodes', 'subtracted', 'filotypes']


def convertMasterNodesFromNumpy(masterNodesNp):
    r, c = masterNodesNp.shape
    masterNodesArray = emptyArrayMatrix(r, c)
    for row in range(r):
        for col in range(c):
            masterNodesArray[row][col] = (masterNodesNp[row, col][0] - 1).tolist()
    return masterNodesArray



def calculateResults(path='data/movie5local.mat'):
    results = {}
    fullState = importFromMatlab(path)
    trees = fullState.trees

    allTDBL = [TDBL(tree, excludeAxon=True, excludeBasal=False, includeFilo=False, filoDist=5) for tree in trees]
    results['tdbl'] = np.array(allTDBL)

    filoTypes, added, subtracted, transitioned, masterChanged, masterNodes = \
        addedSubtractedTransitioned(trees, excludeAxon=True, excludeBasal=False, terminalDist=5, filoDist=5)
    results['filotypes'] = np.vectorize(lambda t: t.value)(filoTypes)
    results['added'] = added
    results['subtracted'] = subtracted
    results['transitioned'] = transitioned
    results['masterChanged'] = masterChanged
    results['masterNodes'] = masterNodes

    motilities, filoLengths = motility(trees, excludeAxon=True, excludeBasal=False, terminalDist=5, filoDist=5)
    results['filolengths'] = filoLengths

    return results

def loadAnswers(path='data/testMotility.mat'):
    answers = {}
    mat = scipy.io.loadmat(path)
    for key in PROPERTIES:
        if key in ['filolengths', 'tdbl']:
            answers[key] = mat[key]
        else:
            answers[key] = mat[key][0][0]
    answers['added'] = (answers['added'] == 1)
    answers['subtracted'] = (answers['subtracted'] == 1)
    answers['transitioned'] = (answers['transitioned'] == 1)
    answers['masterChanged'] = (answers['masterChanged'] == 1)
    answers['masterNodes'] = convertMasterNodesFromNumpy(answers['masterNodes'])
    return answers

def nanCompare(a, b):
    if type(a) is list:
        return a == b
    if a.dtype.kind == 'b':
        a, b = a * 1, b * 1
    with np.errstate(invalid='ignore'):
        return ((np.abs(a - b) < 1e-9) | (np.isnan(a) & np.isnan(b)))

def main():
    results = calculateResults()
    answers = loadAnswers()

    np.set_printoptions(precision=3)
    print ("\nResults:\n---------")

    VIDS = slice(0, 5)
    for prop in PROPERTIES:
        if np.all(nanCompare(answers[prop][VIDS], results[prop][VIDS])):
            print ("Property %s matches! 🙌" % (prop))
        else:
            print ("Property %s doesn't match!" % (prop))
            print ("Expected: ")
            print (answers[prop][VIDS])
            print ("Actual: ")
            print (results[prop][VIDS])
            print ("Match: ")
            print (nanCompare(answers[prop][VIDS], results[prop][VIDS]))




if __name__ == '__main__':
    main()
