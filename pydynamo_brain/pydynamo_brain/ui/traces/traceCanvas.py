import numpy as np

from pydynamo_brain.files import TraceCache
from pydynamo_brain.ui.baseMatplotlibCanvas import BaseMatplotlibCanvas

import pydynamo_brain.util as util

_TRACE_CACHE = TraceCache()

# Draws a dendritic tree in 3D space that can be rotated by the user.
class TraceCanvas(BaseMatplotlibCanvas):
    def __init__(self, parent, fullState, *args, **kwargs):
        self.fullState = fullState
        self.pointsToShow = [] # Order matters
        self.tracesToShow = []
        self.split = True

        super(TraceCanvas, self).__init__(*args, in3D=False, **kwargs)

        self.axes[0].patch.set_facecolor('black')
        vPad, hPad = 0.05, 0.1
        self.fig.subplots_adjust(top=1.0-vPad, bottom=vPad, right=1.0-hPad, left=hPad)

    def compute_initial_figure(self):
        # Initial figure, also used on update.
        ax = self.axes[0]

        self.tracesToShow = []
        for (wID, pID) in self.pointsToShow:
            print ("Point %s in window %d" % (str(pID), wID))

            trace = None
            if wID < len(self.fullState.traces):
                tracePaths = self.fullState.traces[wID]
                trace = _TRACE_CACHE.getTraceForPOI(tracePaths, pID, verbose=True)

            if trace is not None:
                self.tracesToShow.append((pID, wID, trace))
            else:
                print ("  -> No trace! Skipping")

        if len(self.tracesToShow) == 0:
            return

        maxV = np.max([np.max(t[2].data) for t in self.tracesToShow])
        minV = np.min([np.min(t[2].data) for t in self.tracesToShow])

        perLineOffset = 0 if not self.split else maxV - minV

        for i, (pID, wID, trace) in enumerate(self.tracesToShow):
            data, hz = trace.data, trace.rate
            x = np.arange(len(data)) * (1 / hz) # Samples -> Seconds
            y = data
            off = len(self.tracesToShow) - 1 - i
            ax.plot(x, y + off * perLineOffset, label="%s @ %s" % (pID, wID))
            if i == 0 or self.split:
                ax.axhline(off * perLineOffset, ls=':', c='k')

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
