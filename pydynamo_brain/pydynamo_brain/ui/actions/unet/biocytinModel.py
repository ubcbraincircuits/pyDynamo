import os
import copy
import numpy as np
import torch
import torch.nn.functional as F
import pathlib

from tifffile import imread
from . import inferencingUnet as inf
from skimage.filters import gaussian
from skimage.morphology import (
    skeletonize_3d, dilation, disk, ball, label, remove_small_objects
)
from scipy.ndimage import binary_dilation, binary_erosion


def returnBiocytin(imageStack):



    # Set device (GPU/CPU)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(device)
    path = pathlib.Path(__file__).parent.resolve()
    model_path = path / "models" / "unet_trained_model_64v3.pth" 

    loaded_model = inf.load_model(model_path, device, in_channels=1, classes=1)

    stackResults = inf.sliding_window_inference_raw(loaded_model, imageStack, device, window_size=64, stride=32, batch_size=128)

    np.save("results.npy", stackResults)

    stackResults = gaussian(stackResults, sigma=1.5)
    stackResults = (stackResults>.035).astype(int)
    
    stackResults = skeletonize_3d(stackResults)
    np.save("testSkelly.npy", stackResults)
    results = inf.fast2DClean(stackResults, (stackResults.shape[0], 256, 256), (1,128,128), 3, 35, connectivity=2)
    results = inf.orthoCleanUp(results, 45)
    np.save("testSkelly_Clean.npy", results)

    """

    _test = results.copy()
    _test = dilation(_test, ball(3))    
    _test = label((np.max(_test, axis=0)))
    _data = inf.get_largest_label(_test)
    _test[_test!=_data] = 0
    _test = dilation(_test)

    for i in range(results.shape[0]):
        results[i, : , :] =  results[i, : , :]*_test

    #### NEW STUFF
    _test = label(results)
    _data = inf.get_largest_label(_test)
    _test[_test!=_data]=0
    _test[_test!=0]=1

    results[_test==1]=0
    results = inf.windowScan3D(results, (512,512), (512,512), binary_dilation, structure=ball(3))
    results = inf.window_3d(results.astype(bool), (results.shape[0], 512, 512), (1,512,512), remove_small_objects, min_size=850, connectivity=0)
    results[_test==1] = 1
    del _test

    _test = label(results)
    _data = inf.get_largest_label(_test)
    _test[_test!=_data]=0
    _test[_test!=0]=1
    results = _test


    # Step 1: Apply window-based preprocessing in-place
    results = inf.window_preprocess_inplace(results.astype(np.uint8), (results.shape[0], 512, 512), (1, 512, 512))
    """
    return results
