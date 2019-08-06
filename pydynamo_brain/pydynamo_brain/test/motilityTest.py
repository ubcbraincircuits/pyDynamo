import numpy as np
import scipy.io
import tempfile

from pydynamo_brain.analysis import addedSubtractedTransitioned, motility, TDBL
from pydynamo_brain.util import emptyArrayMatrix
from pydynamo_brain.model import *

import pydynamo_brain.files as files

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
    if path.endswith('.mat'):
        # Keep orphans around, to match against old matlab analysis
        fullState = files.importFromMatlab(path, removeOrphanBranches=False)
    else:
        assert path.endswith('.dyn.gz')
        fullState = files.loadState(path)
    trees = fullState.trees

    TERM_DIST = 5
    FILO_DIST = 5

    allTDBL = [TDBL(tree, excludeAxon=True, excludeBasal=False, includeFilo=False, filoDist=FILO_DIST) for tree in trees]
    results['tdbl'] = np.array([allTDBL])

    filoTypes, added, subtracted, transitioned, masterChanged, masterNodes = \
        addedSubtractedTransitioned(trees, excludeAxon=True, excludeBasal=False, terminalDist=TERM_DIST, filoDist=FILO_DIST)
    results['filotypes'] = np.vectorize(lambda t: t.value)(filoTypes)
    results['added'] = added
    results['subtracted'] = subtracted
    results['transitioned'] = transitioned
    results['masterChanged'] = masterChanged
    results['masterNodes'] = masterNodes

    motilities, filoLengths = motility(trees, excludeAxon=True, excludeBasal=False, terminalDist=TERM_DIST, filoDist=FILO_DIST)
    results['filolengths'] = filoLengths

    return fullState, results

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
    if a.shape != b.shape:
        return False
    with np.errstate(invalid='ignore'):
        return ((np.abs(a - b) < 1e-9) | (np.isnan(a) & np.isnan(b)))

def testSimpleAST():
    fullState, results = calculateResults('data/astTest.dyn.gz')
    print (results['filotypes'])
    print (results['added'])
    print (results['subtracted'])
    print (results['transitioned'])

def testAgainstGoldenFile():
    _, results = calculateResults()
    answers = loadAnswers()

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

def testRoundtrip():
    fullState, resultsFromImport = calculateResults(path='data/movie5local.mat')

    tmpFile = tempfile.NamedTemporaryFile(suffix='.dyn.gz')
    print ("   >> saving to tmp file %s..." % (tmpFile.name))
    files.saveState(fullState, tmpFile.name)
    _, resultsFromSave = calculateResults(path=tmpFile.name)
    tmpFile.close()

    print ("\nResults:\n---------")
    VIDS = slice(0, 5)
    for prop in PROPERTIES:
        if np.all(nanCompare(resultsFromImport[prop][VIDS], resultsFromSave[prop][VIDS])):
            print ("Property %s matches! 🙌" % (prop))
        else:
            print ("Property %s doesn't match!" % (prop))
            print ("From Import: ")
            print (resultsFromImport[prop][VIDS])
            print ("From Save: ")
            print (resultsFromSave[prop][VIDS])
            print ("Match: ")
            print (nanCompare(resultsFromImport[prop][VIDS], resultsFromSave[prop][VIDS]))

def testImportNoChange(path='data/localFirst.dyn.gz'):
    print ("Testing no motility changes after nodes copied...")
    fullState = files.loadState(path)
    assert len(fullState.trees) == 1

    treeA = fullState.trees[0]

    # NOTE: old trees sometimes have empty branches:
    emptyBranches = [b for b in treeA.branches if len(b.points) == 0]
    for emptyBranch in emptyBranches:
        treeA.removeBranch(emptyBranch)

    treeB = Tree()
    treeB.clearAndCopyFrom(treeA, fullState)
    treeB._parentState = treeA._parentState
    # Copy branch and point IDs:
    for i in range(len(treeA.branches)):
        treeB.branches[i].id = treeA.branches[i].id
        for j in range(len(treeA.branches[i].points)):
            treeB.branches[i].points[j].id = treeA.branches[i].points[j].id
    trees = [treeA, treeB]

    print ("\nResults:\n---------")

    # TDBL the same for identical trees
    allTDBL = [TDBL(tree, excludeAxon=True, excludeBasal=False, includeFilo=False, filoDist=5) for tree in trees]
    # print (allTDBL)
    assert allTDBL[0] == allTDBL[1]
    print ("🙌 TDBL match!")

    filoTypes, added, subtracted, transitioned, masterChanged, masterNodes = \
        addedSubtractedTransitioned(trees, excludeAxon=True, excludeBasal=False, terminalDist=5, filoDist=5)

    assert not np.any(added)
    assert not np.any(subtracted)
    assert not np.any(transitioned)
    print ("🙌 Nothing added, subtracted or transitioned!")

    motilities, filoLengths = motility(trees, excludeAxon=True, excludeBasal=False, terminalDist=5, filoDist=5)
    mot = motilities['raw'][0]
    assert np.all(np.logical_or(mot == 0, np.isnan(mot)))
    assert np.all(np.logical_or(filoLengths[0] == filoLengths[1], np.isnan(filoLengths[0])))

    filoTypes = np.vectorize(lambda t: t.value)(filoTypes)
    assert np.array_equal(filoTypes[0], filoTypes[1])
    print ("🙌 Filotypes, filo lengths match!")

def run():
    np.set_printoptions(precision=3)
    testSimpleAST()
    testAgainstGoldenFile()
    testRoundtrip()
    testImportNoChange()
    np.set_printoptions()
    return True

if __name__ == '__main__':
    run()
