import torch
import segmentation_models_pytorch as smp
import albumentations as A
from albumentations.pytorch import ToTensorV2
import numpy as np
import torch.nn.functional as F

from tqdm import trange, tqdm

from skimage.morphology import skeletonize_3d, remove_small_objects, dilation, disk, ball, erosion
from scipy.ndimage import binary_dilation, binary_erosion, gaussian_filter

import copy
from skimage.morphology import remove_objects_by_distance, label, remove_small_objects
from skimage.measure import regionprops




def load_model(model_path, device, in_channels=1, classes=1):
    model = smp.UnetPlusPlus( #smp.UnetPlusPlus(
        encoder_name="resnet34",        # Choose encoder, e.g., resnet34, efficientnet-b0, etc.
        encoder_depth=5,
        encoder_weights="imagenet",     # Use pre-trained weights for the encoder
        in_channels=1,                  # Input channels (grayscale images)
        classes=1,                       # Output channels (binary segmentation, 1 class)
        decoder_channels=(64, 64, 32, 32, 16) 
    )

    # Load the trained weights into the model
    model.load_state_dict(torch.load(model_path, map_location=torch.device('cpu'), weights_only=True))
    
    # Move the model to GPU if available
    model = model.to(device)
    
    print(f"Model loaded from {model_path}")
    
    return model


def get_val_transform():
    return A.Compose([
        A.Resize(64, 64),  # Change this to match your window size if needed
        A.Normalize(mean=(0.5,), std=(0.25,)),
        ToTensorV2()
    ])
# Define the batch inference function

def batch_inference(model, crops, device, batch_size=32):
    model.eval()
    results = []
    with torch.no_grad():
        for i in range(0, len(crops), batch_size):
            batch = torch.stack(crops[i:i + batch_size]).to(device)
            preds = model(batch)
            results.append(preds.cpu())
    return torch.cat(results, dim=0)
# Define dynamic thresholding function
def dynamic_threshold(pred_mask, base_threshold=0.12, low_confidence_threshold=0.0185):
    mean_confidence = pred_mask.max().item()
    
    if mean_confidence >= base_threshold:
        threshold = low_confidence_threshold  # Lower the threshold to capture more neuron pixels
    else:
        threshold = base_threshold
    
    return (pred_mask > threshold).astype(np.float32)

def sliding_window_inference(model, image_stack, device, window_size=512, stride=256, batch_size=16, threshold=0.5):
    """
    Perform sliding window inference on a 3D image stack with single-channel (grayscale) images.
    
    :param model: Trained PyTorch model
    :param image_stack: 3D NumPy array of shape (depth, height, width)
    :param window_size: Size of the sliding window (assumes square window)
    :param stride: Stride of the sliding window (how far to move the window after each step)
    :param batch_size: Number of windows to process in parallel
    :param threshold: Threshold for converting probability maps to binary masks
    :return: 3D NumPy array of predicted masks (depth, height, width)
    """
    model.eval()  # Set model to evaluation mode
    depth, height, width = image_stack.shape
    predicted_stack = np.zeros((depth, height, width), dtype=np.float32)

    # Initialize the validation transform
    transform = get_val_transform()

    # Slide over each slice in the stack
    for d in trange(depth):
        image_slice = image_stack[d]  # Single 2D slice (single-channel)

        # Initialize an empty prediction mask for this slice
        predicted_mask = np.zeros((height, width), dtype=np.float32)
        count_mask = np.zeros((height, width), dtype=np.float32)

        # Collect windows for batch inference
        windows = []
        positions = []

        # Apply sliding window and collect all windows
        for y in range(0, height - window_size + 1, stride):
            for x in range(0, width - window_size + 1, stride):
                window = image_slice[y:y+window_size, x:x+window_size]
                
                # Apply the same validation transform as used during training
                transformed = transform(image=window)
                transformed_window = transformed['image']  # This is now a tensor

                windows.append(transformed_window)  # Already a tensor after transformation
                positions.append((y, x))  # Store the top-left position of the window

        # Perform batched inference on all windows
        predictions = batch_inference(model, windows, device, batch_size=batch_size)

        # Place the predictions back into the full mask
        for (y, x), pred_window in zip(positions, predictions):
            pred_window = torch.sigmoid(pred_window).squeeze().numpy()  # Apply sigmoid activation

            # Apply the threshold to binarize the prediction
            #pred_window = (pred_window > threshold).astype(np.float32)
            pred_window = dynamic_threshold(pred_window, threshold)
            
            predicted_mask[y:y+window_size, x:x+window_size] += pred_window
            count_mask[y:y+window_size, x:x+window_size] += 1

        # Normalize the prediction mask by the number of overlapping predictions
        predicted_mask /= np.maximum(count_mask, 1)
        predicted_stack[d] = predicted_mask.astype(np.int8)
    
    return predicted_stack

def sliding_window_inference_raw(model, image_stack, device, window_size=512, stride=256, batch_size=16):
    """
    Perform sliding window inference on a 3D image stack with single-channel (grayscale) images.
    
    :param model: Trained PyTorch model
    :param image_stack: 3D NumPy array of shape (depth, height, width)
    :param window_size: Size of the sliding window (assumes square window)
    :param stride: Stride of the sliding window (how far to move the window after each step)
    :param batch_size: Number of windows to process in parallel
    :param threshold: Threshold for converting probability maps to binary masks
    :return: 3D NumPy array of predicted masks (depth, height, width)
    """
    model.eval()  # Set model to evaluation mode
    depth, height, width = image_stack.shape
    predicted_stack = np.zeros((depth, height, width), dtype=np.float32)

    # Initialize the validation transform
    transform = get_val_transform()

    # Slide over each slice in the stack
    for d in trange(depth):
        image_slice = image_stack[d]  # Single 2D slice (single-channel)

        # Initialize an empty prediction mask for this slice
        predicted_mask = np.zeros((height, width), dtype=np.float32)
        count_mask = np.zeros((height, width), dtype=np.float32)

        # Collect windows for batch inference
        windows = []
        positions = []

        # Apply sliding window and collect all windows
        for y in range(0, height - window_size + 1, stride):
            for x in range(0, width - window_size + 1, stride):
                window = image_slice[y:y+window_size, x:x+window_size]
                
                # Apply the same validation transform as used during training
                transformed = transform(image=window)
                transformed_window = transformed['image']  # This is now a tensor

                windows.append(transformed_window)  # Already a tensor after transformation
                positions.append((y, x))  # Store the top-left position of the window

        # Perform batched inference on all windows
        predictions = batch_inference(model, windows, device, batch_size=batch_size)

        # Place the predictions back into the full mask
        for (y, x), pred_window in zip(positions, predictions):
            pred_window = torch.sigmoid(pred_window).squeeze().numpy()  # Apply sigmoid activation
           
            predicted_mask[y:y+window_size, x:x+window_size] += pred_window
            count_mask[y:y+window_size, x:x+window_size] += 1

        # Normalize the prediction mask by the number of overlapping predictions
        predicted_mask /= np.maximum(count_mask, 1)
        predicted_stack[d] = predicted_mask
    
    return predicted_stack



def clean_and_remove_objects(arr, min_distance):
    """
    Cleans the image by removing small objects and those far away from the largest object.
    
    Parameters:
    - arr: Input binary image (2D or 3D).
    - min_distance: Minimum distance allowed between objects.
    
    Returns:
    - The cleaned binary image with unwanted objects removed.
    """
    # Step 1: Label the binary image
    labeled_arr = label(arr)
    
    # Step 2: Calculate region properties
    regions = regionprops(labeled_arr)
    
    # Step 3: Create a priority array based on the area of the labels (larger objects get higher priority)
    priority = np.zeros(np.amax(labeled_arr) + 1, dtype=np.float32)
    for region in regions:
        priority[region.label] = region.area
    
    # Step 4: Remove objects by distance and priority
    filtered_arr = remove_objects_by_distance(labeled_arr, min_distance, priority=priority)
    
    # Step 5: Find the largest object label
    largest_label = get_largest_label(filtered_arr)
    
    # Step 6: Set the largest object to zero in the filtered array
    filtered_arr[filtered_arr == largest_label] = 0
    
    # Step 7: Set the original image to zero where filtered_arr is not zero
    arr[filtered_arr != 0] = 0
    
    return arr

def get_largest_label(labeled_arr):
    """
    Finds the label of the largest object in a labeled array.
    
    Parameters:
    - labeled_arr: Input labeled array (as from skimage.measure.label).
    
    Returns:
    - The label of the largest object.
    """
    # Get region properties
    regions = regionprops(labeled_arr)
    
    # Find the region with the largest area
    largest_region = max(regions, key=lambda region: region.area)
    
    return largest_region.label


def fast2DClean(arr, window_shape, step=(1, 1, 1), ds=4, size=600, connectivity=2):
    """
    Apply a function to sliding windows over a 3D array and reconstruct the array with lower memory usage.

    Parameters:
    - arr: Input 3D array
    - window_shape: Tuple of 3 integers specifying the window size (depth, height, width)
    - step: Tuple of 3 integers specifying the stride of the window in each dimension (depth, height, width)
    - function: Function to apply to each window. If None, just return the window.
    - kwargs: Additional keyword arguments to pass to the function.

    Returns:
    - The reconstructed 3D array after applying the function to each window.
    """
    depth, height, width = arr.shape
    d_win, h_win, w_win = window_shape
    d_step, h_step, w_step = step

    # Use the same dtype as the input array to reduce memory usage
    #reconstructed_arr = np.zeros_like(arr, dtype=arr.dtype)
    projection = np.max(arr, axis=0)
    #projection = dilation(projection, disk(ds))
    clean = remove_small_objects(projection.astype(bool), size, connectivity=connectivity)  
    clean = clean_and_remove_objects(clean.astype(int), min_distance=35)

    for h in trange(0, height - h_win + 1, h_step):
        for w in range(0, width - w_win + 1, w_step):
            if np.max(clean[h:h + h_win, w:w + w_win]) == False:
               arr[:, h:h + h_win, w:w + w_win] = 0
            else:
                clean_3d = np.expand_dims(clean[h:h + h_win, w:w + w_win], axis=0) 
                clean_3d = np.repeat(clean_3d, arr.shape[0], axis=0)  # Repeat the mask along the depth axis
                arr[:, h:h + h_win, w:w + w_win][clean_3d == 0] = 0
        if np.max(clean[h:h + h_win, w:]) == 0:
           arr[:, h:h + h_win, w:] = 0
        else:
            clean_3d = np.expand_dims(clean[h:h + h_win, w:], axis=0) 
            clean_3d = np.repeat(clean_3d, arr.shape[0], axis=0)  # Repeat the mask along the depth axis
            arr[:, h:h + h_win, w:][clean_3d == 0] = 0
 
    return arr
    
def window_3dExpand(arr, window_shape, step=(1, 1, 1), ds=5, function=None, **kwargs):
    """
    Apply a function to sliding windows over a 3D array and reconstruct the array with lower memory usage.

    Parameters:
    - arr: Input 3D array
    - window_shape: Tuple of 3 integers specifying the window size (depth, height, width)
    - step: Tuple of 3 integers specifying the stride of the window in each dimension (depth, height, width)
    - function: Function to apply to each window. If None, just return the window.
    - kwargs: Additional keyword arguments to pass to the function.

    Returns:
    - The reconstructed 3D array after applying the function to each window.
    """
    depth, height, width = arr.shape
    d_win, h_win, w_win = window_shape
    d_step, h_step, w_step = step

    # Use the same dtype as the input array to reduce memory usage
    reconstructed_arr = np.zeros_like(arr, dtype=arr.dtype)

    
    for h in trange(0, height - h_win + 1, h_step):
        for w in range(0, width - w_win + 1, w_step):
            
            window = copy.deepcopy(arr[:, h:h + h_win, w:w + w_win])
            
            if np.max(window) > 0 or np.max(window)==True:
                window = binary_dilation(window, ball(ds))
                result = function(window, **kwargs)
                # Place the result back into the reconstructed array
                reconstructed_arr[:, h:h + h_win, w:w + w_win] = result
    window = arr[:, h:, w:]
    result = function(window, **kwargs)
    reconstructed_arr[:, h:, w:] = result

    return reconstructed_arr



def window_3d(arr, window_shape, step=(1, 1, 1), function=None, **kwargs):
    """
    Apply a function to sliding windows over a 3D array and reconstruct the array with lower memory usage.

    Parameters:
    - arr: Input 3D array
    - window_shape: Tuple of 3 integers specifying the window size (depth, height, width)
    - step: Tuple of 3 integers specifying the stride of the window in each dimension (depth, height, width)
    - function: Function to apply to each window. If None, just return the window.
    - kwargs: Additional keyword arguments to pass to the function.

    Returns:
    - The reconstructed 3D array after applying the function to each window.
    """
    depth, height, width = arr.shape
    d_win, h_win, w_win = window_shape
    d_step, h_step, w_step = step

    # Use the same dtype as the input array to reduce memory usage
    reconstructed_arr = np.zeros_like(arr, dtype=arr.dtype)

    
    for h in trange(0, height - h_win + 1, h_step):
        for w in range(0, width - w_win + 1, w_step):
            
            window = copy.deepcopy(arr[:, h:h + h_win, w:w + w_win])
            if np.max(window) > 0 or np.max(window)==True:

                result = function(window, **kwargs)
                # Place the result back into the reconstructed array
                reconstructed_arr[:, h:h + h_win, w:w + w_win] = result
    window = arr[:, h:, w:]
    result = function(window, **kwargs)
    reconstructed_arr[:, h:, w:] = result

    return reconstructed_arr
    
from skimage.filters import gaussian 
def windowSkel(arr):
        data = arr.copy()
        data = binary_dilation(data, ball(3))
        blur = gaussian(data.astype(float))
        data = skeletonize_3d(blur)
        return data.astype(int)             

def orthoClean(stackResults, slice_step=126, obj_size=300, connectivity=0):
    """
    Function to process a 3D image stack, remove small objects from projection slices,
    and clean the original stack based on projection results.
    
    Parameters:
    - stackResults: 3D numpy array representing the image stack.
    - slice_step: Step size for slicing through the stack (default: 126).
    - obj_size: Minimum size of objects to retain (default: 300).
    - connectivity: The connectivity to define the neighborhood for objects (default: 0).
    
    Returns:
    - orthoClean: Cleaned version of the input stack.
    """
    
    orthoClean = stackResults.copy()
    j = 0
    
    for i in range(slice_step, stackResults.shape[1], slice_step):
       
        max_projection = np.max(stackResults[:, j:i, :], axis=1)
        
        _cleanSlice = remove_small_objects(max_projection.astype(bool), obj_size, connectivity=connectivity)
        # Define some dimensions and start processing
        l = max_projection.shape[1] // 2
        m = 0
        _cleanSlice = _cleanSlice.astype(np.uint)
        
        # Clean the original stack based on the projections
        for n in range(0, max_projection.shape[1], slice_step):
            if np.sum(_cleanSlice[:l, m:n]) == 0:
                orthoClean[:l, j:i, m:n] = 0
            if np.sum(_cleanSlice[l:, m:n]) == 0:
                orthoClean[l:, j:i, m:n] = 0
                
        j = i
   
    return orthoClean



def windowScan3D(arr, window_shape, step=(1, 1), function=None, **kwargs):
    """
    Apply a function to sliding windows over a 3D array and reconstruct the array with lower memory usage.

    Parameters:
    - arr: Input 3D array
    - window_shape: Tuple of 3 integers specifying the window size (depth, height, width)
    - step: Tuple of 3 integers specifying the stride of the window in each dimension (depth, height, width)
    - function: Function to apply to each window. If None, just return the window.
    - kwargs: Additional keyword arguments to pass to the function.

    Returns:
    - The reconstructed 3D array after applying the function to each window.
    """
    _, height, width = arr.shape
    h_win, w_win = window_shape
    h_step, w_step = step

    # Use the same dtype as the input array to reduce memory usage
    reconstructed_arr = np.zeros_like(arr, dtype=arr.dtype)
   
    for w in trange(0, width - w_win + 1, w_step):
        for h in trange(0, height - h_win + 1, h_step):
            window = copy.deepcopy(arr[:, h:h + h_win, w:w + w_win])
            if np.max(window) > 0 or np.max(window)==True:
    
                result = function(window, **kwargs)
                # Place the result back into the reconstructed array
                reconstructed_arr[:, h:h + h_win, w:w + w_win] = result


    return reconstructed_arr


def window_preprocess_inplace(arr, window_shape, step):
    """
    Process the array using smaller windows to apply dilation and blurring in-place,
    avoiding large float arrays in memory.
    """
    depth, height, width = arr.shape
    d_win, h_win, w_win = window_shape
    d_step, h_step, w_step = step


    for h in trange(0, height - h_win + 1, h_step):
        for w in range(0, width - w_win + 1, w_step):
            # Extract the window
            if np.max(arr[:, h:h + h_win, w:w + w_win]) > 0 or np.max(arr[:, h:h + h_win, w:w + w_win])==True:
                window = arr[:, h:h + h_win, w:w + w_win].copy()
            
                # Apply dilation to the window
                #window = binary_dilation(window, ball(5)).astype(np.uint8)

                # Apply Gaussian blur (temporary float array)
                window = gaussian_filter(window.astype(np.float32), 1)
                
                window *= 255
                # Convert the blurred result back to int and update the original array
                arr[:, h:h + h_win, w:w + w_win] = window.astype(np.uint8)
    return arr


def orthoCleanUp(arr, size=25, connections=3, distance=25):

    orthoProj = np.max(arr, axis=1)
    orthoProj = remove_small_objects(orthoProj.astype(bool), 25, 3)
    orthoProj = clean_and_remove_objects(orthoProj, distance)
    
    arr = arr.astype(np.int8)

    clean_3d = np.expand_dims(orthoProj, axis=1) 
    clean_3d = np.repeat(clean_3d, arr.shape[1], axis=1).astype(np.int8)  # Repeat the mask along the depth axis
    
    clean_3d *= arr
    return clean_3d