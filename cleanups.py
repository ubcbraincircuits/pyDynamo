# A collection of small scripts to clean up existing dynamo files.

import os
import sys
from PyQt5 import QtWidgets

import files

# Either use a provided path, or open a filepicker to select one.
def usePathOrPick(path=None):
    if path is not None:
        return path
    app = QtWidgets.QApplication([])
    filePath, _ = QtWidgets.QFileDialog.getOpenFileName(None,
        "Open dynamo save file", "", "Dynamo files (*.dyn.gz)"
    )
    return str(filePath)

# Due to errors in earlier dynamo, empty branches do not get removed.
# This goes and removes every branch with no points from the file.
def cleanupEmptyBranches(fullState):
    print ("Processing trees...")
    for i, tree in enumerate(fullState.trees):
        removed = tree.cleanEmptyBranches()
        print ("  Tree %d: %d branches removed" % (i, removed))
    print ()

# Load the state, and perform the cleanups
def doCleanups(path):
    origPath = usePathOrPick(path)
    fullState = files.loadState(origPath)
    cleanupEmptyBranches(fullState)
    # TODO - add more cleanups here
    cleanPath = os.path.join(os.path.dirname(origPath), "clean." + os.path.basename(origPath))
    files.saveState(fullState, cleanPath)
    print ("State saved to %s" % cleanPath)

if __name__ == '__main__':
    path = sys.argv[1] if len(sys.argv) > 1 else None
    doCleanups(path)
