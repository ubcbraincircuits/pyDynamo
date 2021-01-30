from functools import cmp_to_key
import numpy as np

from matplotlib.ticker import FuncFormatter
from scipy import signal

from pydynamo_brain.files import TraceCache
from pydynamo_brain.ui.baseMatplotlibCanvas import BaseMatplotlibCanvas
from pydynamo_brain.ui.common import createAndShowInfo

import pydynamo_brain.util as util

_TRACE_CACHE = TraceCache()

# Utility to pad (min, max) range by a small amount and return the new ones
def _addPad(lo, hi, pad):
    mid = (lo + hi) / 2
    haf = hi - mid
    return mid - (1 + pad) * haf, mid + (1 + pad) * haf

# Combine similar traces, by sorting by hz (first) and samples (second)
def _traceCompare(idAndTraceA, idAndTraceB):
    idA, traceA = idAndTraceA
    idB, traceB = idAndTraceB

    if traceA.rate != traceB.rate:
        return traceA.rate - traceB.rate
    if len(traceA.data) != len(traceB.data):
        return len(traceA.data) - len(traceB.data)
    return 1 if idA < idB else -1

_TRACE_COMPARE_KEY = cmp_to_key(_traceCompare)

# Draws all traces from one timepoint as an intensity plot
class AllTracesCanvas(BaseMatplotlibCanvas):
    def __init__(self, parent, fullState, treeIdx, *args, **kwargs):
        tracePaths = []
        if treeIdx < len(fullState.traces):
            tracePaths = fullState.traces[treeIdx]

        self.allTraces = _TRACE_CACHE.getAllTraces(tracePaths)
        self.allTraceWindow = parent
        self.intensity = None # Hacky, but this gets set in the figure creation
        self.colorbar = None

        super(AllTracesCanvas, self).__init__(parent, *args, in3D=False, **kwargs)

        self.updateColorbarHack()

    def compute_initial_figure(self):
        infoBox = createAndShowInfo("Applying filters...", self.allTraceWindow)

        # Initial figure, also used on update.
        ax = self.axes[0]

        everyIdAndTrace = list(self.allTraces.items())
        everyIdAndTrace.sort(key=_TRACE_COMPARE_KEY)
        nTraces = len(everyIdAndTrace)

        if nTraces == 0:
            print ("No traces :( Skipping intensity plot")
            return

        maxSec, hzAtMax, lenAtMax = None, None, None
        for (id, trace) in everyIdAndTrace:
            traceSec = len(trace.data) / trace.rate
            if maxSec is None or maxSec < traceSec:
                maxSec, hzAtMax, lenAtMax = traceSec, trace.rate, len(trace.data)

        resultPlot = np.zeros((nTraces, lenAtMax))

        for idx, (id, trace) in enumerate(everyIdAndTrace):
            samples = self.allTraceWindow.applyFilters(trace.data, trace.rate)

            if trace.rate != hzAtMax:
                traceSec = len(samples) / trace.rate
                targetLen = int(traceSec * hzAtMax)
                samples = signal.resample(samples, targetLen)

            resultPlot[idx, :len(samples)] = samples

        self.intensity = ax.imshow(resultPlot, cmap='hot')

        ax.set_title(self.allTraceWindow.getTitle())

        # X axis is time
        ax.get_xaxis().set_major_formatter(FuncFormatter(lambda x, pos: "%.2fs" % (x / hzAtMax)))
        ax.set_xlabel("Time (sec)")

        # Y axis is POI:
        ax.set_ylabel("POI")

        infoBox.hide()

    def needToUpdate(self):
        for ax in self.axes:
            ax.cla()
        self.compute_initial_figure()
        self.updateColorbarHack()
        self.draw()

    def updateColorbarHack(self):
        # Note: matplotlib doesn't like it when you edit the colorbar under it.
        # Currently it keeps shrinking...I need to fix this properly.
        if self.colorbar is not None:
            self.fig.delaxes(self.fig.axes[1])

        vPad, hPad = 0.1, 0.15
        self.fig.subplots_adjust(top=1.0-vPad, bottom=vPad, right=1.0, left=hPad)
        self.colorbar = self.fig.colorbar(self.intensity, ax=self.axes[0], shrink=0.5)
