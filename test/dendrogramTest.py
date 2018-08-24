import matplotlib.pyplot as plt


import files

from ui.dendritePainter import colorForBranch
from ui.dendrogram import calculatePositions

def run(path='test/files/example2.dyn.gz'):
    tree = files.loadState(path).trees[0]
    pointX, pointY = calculatePositions(tree)

    plt.style.use('dark_background')
    for i, b in enumerate(tree.branches):
        if len(b.points) == 0:
            continue
        x, y = [], []
        for p in [b.parentPoint] + b.points:
            x.append(pointX[p.id])
            y.append(pointY[p.id])
        plt.plot(x, y, c=colorForBranch(i), linewidth=0.5)
        # plt.text(x[-1], y[-1], b.id + "\n ", horizontalalignment='center', verticalalignment='center')

    x, y = [], []
    for p in tree.flattenPoints():
        x.append(pointX[p.id])
        y.append(pointY[p.id])
    plt.scatter(x, y, s=10, c='white', marker='D')
    plt.show()
    return True
