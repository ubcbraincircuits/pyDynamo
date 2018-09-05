from PyQt5 import QtWidgets

import sys
import files

from analysis import allTrees, allBranches
from analysis.functions.tree import *
from analysis.functions.branch import *

# Either use a provided path, or open a filepicker to select one.
def usePathOrPick(path):
    if path is not None:
        return path
    app = QtWidgets.QApplication([])
    filePath, _ = QtWidgets.QFileDialog.getOpenFileName(None,
        "Open dynamo save file", "", "Dynamo files (*.dyn.gz)"
    )
    return str(filePath)

# Example of running tree-based analysis
def runTreeAnalysis(path=None):
    # List of analysis functions to produce answers across each tree:
    toRun = [
        pointCount,
        branchCount,
        tdbl
    ]
    # Named arguments passed in to the functions
    arguments = {
        'excludeAxon': False
    }

    result = allTrees(usePathOrPick(path), toRun, **arguments)
    print (result)

# Example of running branch-based runTr
def runBranchAnalysis(path=None):
    # List of analysis functions to produce answers across each tree:
    toRun = [
        branchLengths,
        branchType
    ]
    # Named arguments passed in to the functions
    arguments = {
        'excludeAxon': False
    }

    result = allBranches(usePathOrPick(path), toRun, **arguments)
    print (result)

if __name__ == '__main__':
    # Path is first command-line argument, if provided.
    path = sys.argv[1] if len(sys.argv) > 1 else None
    # runTreeAnalysis(path)
    runBranchAnalysis(path)
