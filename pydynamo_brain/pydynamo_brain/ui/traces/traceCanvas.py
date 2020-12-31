import numpy as np

from pydynamo_brain.files import TraceCache
from pydynamo_brain.ui.baseMatplotlibCanvas import BaseMatplotlibCanvas

import pydynamo_brain.util as util

_TRACE_CACHE = TraceCache()

# Draws a dendritic tree in 3D space that can be rotated by the user.
class TraceCanvas(BaseMatplotlibCanvas):
    def __init__(self, parent, fullState, windowIndex, initialPointID, *args, **kwargs):
        self.fullState = fullState
        self.pointsToShow = set()
        self.pointsToShow.add( (windowIndex, initialPointID) )

        super(TraceCanvas, self).__init__(*args, in3D=False, **kwargs)

    def compute_initial_figure(self):
        ax = self.axes[0]

        tracesToShow = []
        for (wID, pID) in self.pointsToShow:
            print ("Point %s in window %d" % (str(pID), wID))

            trace = None
            if wID < len(self.fullState.traces):
                tracePaths = self.fullState.traces[wID]
                trace = _TRACE_CACHE.getTraceForPOI(tracePaths, pID, verbose=True)

            if trace is not None:
                tracesToShow.append(trace)
            else:
                print ("  -> No trace! Skipping")

        for trace in tracesToShow:
            data, hz = trace.data, trace.rate
            x = np.arange(len(data)) * (1 / hz) # Samples -> Seconds
            y = data
            ax.plot(x, y, label="%s @ %s" % (pID, wID))

        ax.legend()

    def needToUpdate(self):
        for ax in self.axes:
            ax.cla()
        self.compute_initial_figure()
        self.draw()
