import math
import pandas as pd

# Provide the number of puncta drawn in each tree.
def punctaCount(fullState, **kwargs):
    counts = []
    for i in range(len(fullState.trees)):
        if i < len(fullState.puncta):
            counts.append(len(fullState.puncta[i]))
        else:
            counts.append(0)
    return pd.DataFrame({'punctaCount': counts})

# Provide the size of the puncta in each tree.
def totalPunctaSize(fullState, **kwargs):
    totalSizes = []
    for i in range(len(fullState.trees)):
        if i < len(fullState.puncta):
            totalSize = 0
            for p in fullState.puncta[i]:
                totalSize += math.pi * p.radius * p.radius
            totalSizes.append(totalSize)
        else:
            totalSizes.append(0)
    return pd.DataFrame({'totalPunctaSize': totalSizes})

# Provide the average intensity of the puncta in each tree.
def totalPunctaIntensity(fullState, **kwargs):
    raise Exception("Coming soon: Puncta intensity analysis")
