from PyQt5 import QtWidgets

_TEST_FILE_PATHS = None

def setNextTestPaths(testPath=None):
    global _TEST_FILE_PATHS
    _TEST_FILE_PATHS = testPath

def getOpenFileName(parent, caption, directory, filter, multiFile=False, saveFile=False):
    global _TEST_FILE_PATHS
    if _TEST_FILE_PATHS is not None:
        toReturn = _TEST_FILE_PATHS
        _TEST_FILE_PATHS = None
        return toReturn

    result = None
    if saveFile:
        result, _ = QtWidgets.QFileDialog.getSaveFileName( parent, caption, directory, filter)
    elif multiFile:
        result, _ = QtWidgets.QFileDialog.getOpenFileNames(parent, caption, directory, filter)
    else:
        result, _ = QtWidgets.QFileDialog.getOpenFileName( parent, caption, directory, filter)
    return result
