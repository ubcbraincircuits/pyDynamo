import neurom as nm
import numpy as np
import os
import pandas as pd
import tempfile

from typing import Any

import pydynamo_brain.files as files
from pydynamo_brain.model import FullState, Tree

# Convert a fullState tree model object into a NeuroM neuron, via SWC
def treeToNeuroM(fullState: FullState, tree: Tree) -> Any:
    result = None

    tmpFileDir = os.path.basename(__file__)
    with tempfile.NamedTemporaryFile(mode='wt+', suffix='.swc', prefix=tmpFileDir) as tmpFile:
        path = os.path.join(tmpFileDir, tmpFile.name)
        print ("Writing temporary SWC to %s" % path)

        # Step 1: Export to SWC
        files.exportToSWC(tmpFileDir, tmpFile.name, tree, fullState, forNeuroM=True)

        # Step 2: Load SWC into NeuroM data type
        result = nm.load_neuron(path)
    return result

# Perform per-tree NeuroM analysis of a collection of trees
def neuroMAnalysisForNeurons(fullState: FullState) -> pd.DataFrame:
    result = pd.DataFrame()
    neurons = [treeToNeuroM(fullState, tree) for tree in fullState.trees]

    result['paths'] = [os.path.basename(path) for path in fullState.filePaths]
    result['tdbl'] = [np.sum(nm.get('section_lengths', neuron, neurite_type=nm.BASAL_DENDRITE)) for neuron in neurons]
    return result
