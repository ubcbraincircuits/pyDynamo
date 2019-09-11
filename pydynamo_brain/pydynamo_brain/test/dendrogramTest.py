import matplotlib.pyplot as plt

import pydynamo_brain.files as files

from pydynamo_brain.ui.dendrogram import calculatePositions

def run(path='pydynamo_brain/pydynamo_brain/test/files/example2.dyn.gz'):
    tree = files.loadState(path).trees[0]
    pointX, pointY = calculatePositions(tree)

    # TODO: Verify X and Y positions
    return True
