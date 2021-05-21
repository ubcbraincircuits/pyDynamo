import matplotlib
import matplotlib.pyplot as plt

import numpy as np
import numpy.polynomial.polynomial as npPoly

import pydynamo_brain.util as util

from pydynamo_brain.analysis import shollCrossings, shollMetrics
from pydynamo_brain.ui.baseMatplotlibCanvas import BaseMatplotlibCanvas

GREY_COLOUR   = (0.75, 0.75, 0.75, 0.75)

# Draws a dendritic tree in 3D space that can be rotated by the user.
class ShollCanvas(BaseMatplotlibCanvas):

    def __init__(self, parent, fullState, treeModels, *args, **kwargs):

        self.treeModels = treeModels
        self.fullState = fullState
        self.shollViewWindow = parent
        analysisOpt = fullState.projectOptions.analysisOptions
        self.binSizeUm = analysisOpt['shollBinSize'] if 'shollBinSize' in analysisOpt else 5.0

        super(ShollCanvas, self).__init__(parent, *args, in3D=False, **kwargs)

        self.fig.subplots_adjust(top=0.95, bottom=0.2, right=0.95, left=0.2, wspace=0.05, hspace=0.05)


    def compute_initial_figure(self):
        ax  = self.axes[0]
        cmap = matplotlib.cm.get_cmap('viridis')

        BIN_SZ_UM =  self.binSizeUm

        MAX_RAD_UM = 0
        for tree in self.treeModels:
            if tree.spatialRadius() > MAX_RAD_UM:
                MAX_RAD_UM = tree.spatialRadius()
        MAX_RAD_UM += BIN_SZ_UM

        n = len(self.treeModels)

        stacked = []

        for i, tree in enumerate(self.treeModels):
            count, rad = shollCrossings(tree, BIN_SZ_UM, MAX_RAD_UM)
            stacked.append(count)
            ax.plot(rad, count, ':x', c=cmap(i/n), alpha=0.5, lw=1, zorder=1)

        combined = np.array(stacked)
        mean = np.mean(combined, axis=0)
        err = np.std(combined, axis=0)
        ax.errorbar(rad, mean, yerr=err, c='k', lw=2, elinewidth=2, capsize=2, zorder=2)

        ax.set_xlabel("Distance from Soma (μm)", fontsize=18)
        ax.set_ylabel("Intersections", fontsize=18)
        ax.tick_params(axis='both', labelsize=16)
        legend_labels = []
        for tree in self.treeModels:
            legend_labels.append("Tree {}".format(self.treeModels.index(tree)))
        ax.legend(legend_labels)

    def needToUpdate(self):
        for ax in self.axes:
            ax.cla()

        self.compute_initial_figure()
        self.draw()
