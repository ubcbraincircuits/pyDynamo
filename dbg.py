import matplotlib.pyplot as plt

import files

INPUT = 'data/Live4-1-2015_09-16-03.tif'

stack = files.tiffRead(INPUT)
plt.imshow(stack[0])
plt.show()
