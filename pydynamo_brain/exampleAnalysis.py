from PyQt5 import QtWidgets

from mpl_toolkits.mplot3d import Axes3D
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import os
import sys

import pydynamo_brain.files as files
import pydynamo_brain.util as util

from pydynamo_brain.analysis import allTrees, allBranches, addedSubtractedTransitioned, allPuncta
from pydynamo_brain.analysis.neurom import neuroMAnalysisForNeurons
from pydynamo_brain.analysis.functions.tree import *
from pydynamo_brain.analysis.functions.branch import *
from pydynamo_brain.analysis.functions.puncta import *
from pydynamo_brain.model import FiloType

_IMG_CACHE = util.ImageCache()

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
        tdbl,
        shollStats
    ]
    # Named arguments passed in to the functions
    arguments = {
        'excludeAxon': False,
        'excludeBasal': False,
        'shollBinSize': 5.0,
    }

    result = allTrees(usePathOrPick(path), toRun, **arguments)
    pd.DataFrame(result).to_csv("tree_analysis.csv")
    print (result)

# Example of running branch-based runTr
def runBranchAnalysis(path=None):
    # List of analysis functions to produce answers across each tree:
    toRun = [
        branchParentIDs,
        branchLengths,
        branchType,
        branchHasAnnotationFunc('axon', recurseUp=True),
        branchHasAnnotationFunc('basal', recurseUp=True)
    ]
    # Named arguments passed in to the functions
    arguments = {
        'excludeAxon': False,
        'excludeBasal': False
    }

    path = usePathOrPick(path)
    result = allBranches(path, toRun, **arguments)
    outName = os.path.basename(path).replace(".dyn.gz", "_branchAnalysis.csv")
    outPath = os.path.join(os.path.dirname(path), outName)
    pd.DataFrame(result).to_csv(outPath)
    print (result)
    print ("Result saved to %s" % outPath)

# Example of running puncta-based analysis
def runPunctaAnalysis(path=None):
    # List of analysis functions to produce answers across each tree:
    toRun = [
        # punctaCount,
        # totalPunctaSize,
        perPunctaSize,
        perPunctaIntensity
    ]
    # Named arguments passed in to the functions
    arguments = {
        'excludeAxon': False,
        'excludeBasal': False
    }

    result = allPuncta(usePathOrPick(path), toRun, **arguments)
    pd.DataFrame(result).to_csv("puncta_analysis.csv")
    print (result)

# Example of running NeuroM analysis methods against Dynamo trees
def runNeuroMAnalysis(path):
    fullState = files.loadState(usePathOrPick(path))
    # NOTE: need to load one image, so set up volume size
    _IMG_CACHE.handleNewUIState(fullState.uiStates[0])
    print ("Loaded %d trees" % len(fullState.trees))
    result = neuroMAnalysisForNeurons(fullState)
    print (result)

# Example novel analysis: get filopodia tips, plot in 3D, and compare spatial vs tree distance.
def runFiloTipCluster(path):
    fullState = files.loadState(usePathOrPick(path))
    # Process each tree in order:
    for treeIdx, tree in enumerate(fullState.trees):
        branchIDList = util.sortedBranchIDList([tree])

        # Find the types of each branch:
        filoTypes, _, _, _, _, _ = addedSubtractedTransitioned([tree])

        # Keep only interstitial filo...
        interstitialFiloIDs = []
        for branchID, filoType in zip(branchIDList, filoTypes[0]):
            if filoType == FiloType.INTERSTITIAL:
                interstitialFiloIDs.append(branchID)
        print ("%d Interstitial Filos detected" % (len(interstitialFiloIDs)))

        # and map to the points at their tip:
        tipPoints = []
        for branch in tree.branches:
            if branch.id in interstitialFiloIDs:
                if len(branch.points) > 0:
                    tipPoints.append(branch.points[-1])
        fig = plt.figure()
        fig.suptitle("Interstitial Filo Tip clustering for [%d]" % (treeIdx + 1))
        fig.subplots_adjust(left=0.02, bottom=0.07, right=0.98, top=0.9, wspace=0.05, hspace=0.2)

        # 3D plot showing where the filo tips are on the branches.
        ax3D = fig.add_subplot(121, projection='3d')
        ax3D.set_title("3D positions")
        for branch in tree.branches:
            if branch.parentPoint is not None:
                points = [branch.parentPoint] + branch.points
                ax3D.plot(*tree.worldCoordPoints(points), c=(0.5, 0.5, 0.5, 0.1))
        ax3D.scatter(*tree.worldCoordPoints(tipPoints))

        # 2D plot comparing spatial distance to tree distance
        sDs, tDs = [], []
        ax2D = fig.add_subplot(122)
        ax2D.set_title("Spatial distance vs Tree Distance")
        ax2D.set_xlabel("Spatial Distance (uM)")
        ax2D.set_ylabel("Tree Distance (uM)")
        for i, p1 in enumerate(tipPoints):
            for p2 in tipPoints[i+1:]:
                spatialDist, treeDist = tree.spatialAndTreeDist(p1, p2)
                sDs.append(spatialDist)
                tDs.append(treeDist)
        if len(sDs) > 0 and len(tDs) > 0:
            ax2D.scatter(sDs, tDs)
            ax2D.plot([0, np.max(sDs)], [0, np.max(sDs)], '--', c=(0.5, 0.5, 0.5, 0.7))
        plt.show()

if __name__ == '__main__':
    # Path is first command-line argument, if provided.
    path = sys.argv[1] if len(sys.argv) > 1 else None
    runTreeAnalysis(path)
    # runBranchAnalysis(path)
    # runPunctaAnalysis(path)
    # runFiloTipCluster(path)
    # runNeuroMAnalysis(path)
