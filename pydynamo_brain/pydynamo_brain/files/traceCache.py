import pynwb

TRACE_PREFIX = 'POI '

def loadTraces(path, verbose=False):
    try:
        # Note: NWB HD5 traces are lazily ready, so this IO must remain
        # open until we actively read all trace data out of file.
        io = pynwb.NWBHDF5IO(path, 'r+')
        nwbFile = io.read()

        traces = {}
        for key, value in nwbFile.acquisition.items():
            if key.startswith(TRACE_PREFIX):
                nodeID = key[len(TRACE_PREFIX):]
                loadedData = value.data[:] # This is where data is loaded...
                traces[nodeID] = pynwb.base.TimeSeries(
                    name=key,
                    data=loadedData,
                    unit=value.unit,
                    rate=value.rate,
                )
                if verbose:
                    print ("%s: %s values @ %dhz" % (
                        nodeID, traces[nodeID].data.shape, int(traces[nodeID].rate)
                    ))
        return traces



    except Exception as e:
        print ("Error reading file!")
        print (e)
        return None

def loadStim(path, verbose=False):
    try:
        # Note: NWB HD5 traces are lazily ready, so this IO must remain
        # open until we actively read all trace data out of file.
        io = pynwb.NWBHDF5IO(path, 'r+')
        nwbFile = io.read()
        if nwbFile.stimulus is not None:
            for _, value in nwbFile.stimulus.items():
                if value.timestamps is not None:
                    stim = list(value.timestamps)
        else:
            stim = None
        return stim



    except Exception as e:
        print ("Error reading file!")
        print (e)
        return None


class TraceCache:
    """Singleton cache mapping .nwb file path to loaded POI -> NWB TimeSeries maps.

    Used so that the model can store just paths, and traces are lazily loaded only
    when displayed, and not saved to file/history.
    """

    # Singleton instance - create TraceCache() and get back the same cache each time.
    _instance = None
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = object.__new__(TraceCache)
        return cls._instance

    # Maps path string -> map: poi id -> NWB TimeSeries
    _loadedTraces = dict()

    _loadedStim = dict()

    # Returns TimeSeries for POI, possibly loading it first if not yet cached.
    def getStim(self, tracePaths, loadIfMissing=True, verbose=False):
        for path in tracePaths:
            if path not in self._loadedStim and loadIfMissing:
                stimMap = loadStim(path, verbose)
                if stimMap is not None:
                    print('3')

                    self._loadedStim[path] = stimMap
                    print('StimMap: ', stimMap)
                else:
                    self._loadedStim[path] = None

            if path in self._loadedStim:
                return self._loadedStim[path]

        # Not found :(
        return None

    # Returns TimeSeries for POI, possibly loading it first if not yet cached.
    def getTraceForPOI(self, tracePaths, pointID, loadIfMissing=True, verbose=False):
        for path in tracePaths:
            if path not in self._loadedTraces and loadIfMissing:
                traceMap = loadTraces(path, verbose)
                if traceMap is not None:
                    self._loadedTraces[path] = traceMap

            if path in self._loadedTraces and pointID in self._loadedTraces[path]:
                return self._loadedTraces[path][pointID]

        # Not found :(
        return None

    # Returns a list of list of TimeSeries for all POI in the given paths
    def getAllTraces(self, tracePaths):
        mergedTraces = {}

        for path in tracePaths:
            if path not in self._loadedTraces:
                traceMap = loadTraces(path, verbose=False)
                if traceMap is not None:
                    self._loadedTraces[path] = traceMap

            if path in self._loadedTraces and self._loadedTraces[path] is not None:
                for k, v in self._loadedTraces[path].items():
                    mergedTraces[k] = v

        return mergedTraces
