import numpy as np

from matplotlib.ticker import FuncFormatter

from pydynamo_brain.files import TraceCache
from pydynamo_brain.ui.baseMatplotlibCanvas import BaseMatplotlibCanvas

import pydynamo_brain.util as util

_TRACE_CACHE = TraceCache()

# Utility to pad (min, max) range by a small amount and return the new ones
def _addPad(lo, hi, pad):
    mid = (lo + hi) / 2
    haf = hi - mid
    return mid - (1 + pad) * haf, mid + (1 + pad) * haf


# Draws a dendritic tree in 3D space that can be rotated by the user.
class TraceCanvas(BaseMatplotlibCanvas):
    def __init__(self, parent, fullState, *args, **kwargs):
        self.fullState = fullState
        self.pointsToShow = [] # Order matters
        self.tracesToShow = []
        self.split = True
        self.traceViewWindow = parent

        super(TraceCanvas, self).__init__(parent, *args, in3D=False, **kwargs)

        vPad, hPad = 0.1, 0.15
        self.fig.subplots_adjust(top=1.0-vPad, bottom=vPad, right=1.0-hPad, left=hPad)

    def compute_initial_figure(self):
        # Initial figure, also used on update.
        ax = self.axes[0]
        ax.patch.set_facecolor('black')

        self.tracesToShow = []
        for (wID, pID) in self.pointsToShow:
            trace = None
            if wID < len(self.fullState.traces):
                tracePaths = self.fullState.traces[wID]
                trace = _TRACE_CACHE.getTraceForPOI(tracePaths, pID, verbose=False)

            if trace is not None:
                data, hz = trace.data, trace.rate
                samples = self.traceViewWindow.applyFilters(data, hz)
                self.tracesToShow.append((pID, wID, samples, hz))
            else:
                # print ("  -> No trace! Skipping")
                pass

        if len(self.tracesToShow) == 0:
            return

        ax.axvline(0, ls=':', c=(1, 1, 1, 1), lw=0.5)

        maxV = np.max([np.max(t[2].data) for t in self.tracesToShow])
        minV = np.min([np.min(t[2].data) for t in self.tracesToShow])

        perLineOffset = 0 if not self.split else maxV - minV

        minX, maxX, minY, maxY = None, None, None, None

        yZeros = []
        for i, (pID, wID, samples, hz) in enumerate(self.tracesToShow):
            x = np.arange(len(samples)) * (1 / hz) # Samples -> Seconds
            y = samples
            off = len(self.tracesToShow) - 1 - i
            yV = y + off * perLineOffset
            ax.plot(x, yV, label="%s @ %s" % (pID, wID))

            if minX is None:
                minX, maxX = np.min(x), np.max(x)
                minY, maxY = np.min(yV), np.max(yV)
            else:
                minX, maxX = min(minX, np.min(x)), max(maxX, np.max(x))
                minY, maxY = min(minY, np.min(yV)), max(maxY, np.max(yV))

            if off == 0 or self.split:
                ax.axhline(off * perLineOffset, ls=':', c=(1, 1, 1, 0.5), lw=1)
                yZeros.append(off * perLineOffset)
        yZeros = np.array(yZeros)


        # X axis is time
        ax.get_xaxis().set_major_formatter(FuncFormatter(lambda x, pos: "%.2fs" % x))
        ax.set_xlabel("Time (sec)")
        ax.set_xlim(*_addPad(minX, maxX, 0.05))

        # Y axis is value, possibly split
        yTickScale = int(0.7 * maxV)
        yTickPct = self.traceViewWindow.showPercent()
        tickFmt = "%d%%" if yTickPct else "%.2f"
        zeroText, deltaText = tickFmt % (0), tickFmt % (yTickScale * (100 if yTickPct else 1))
        ax.set_yticks(yZeros, minor=False)
        ax.set_yticks(yZeros + yTickScale, minor=True)
        ax.get_yaxis().set_major_formatter(FuncFormatter(lambda x, pos: zeroText))
        ax.get_yaxis().set_minor_formatter(FuncFormatter(lambda x, pos: deltaText))
        ax.set_ylabel(self.traceViewWindow.getYLabel())
        ax.set_ylim(*_addPad(minY, maxY, 0.05))

        ax.legend()

    def needToUpdate(self):
        for ax in self.axes:
            ax.cla()
        self.compute_initial_figure()
        self.draw()

    def togglePointInWindow(self, windowIndex, pointID):
        meta = (windowIndex, pointID)
        if meta in self.pointsToShow:
            self.pointsToShow.remove(meta)
        else:
            self.pointsToShow.append(meta)
        self.needToUpdate()

        # Return whether this is completely empty
        return len(self.tracesToShow) == 0
