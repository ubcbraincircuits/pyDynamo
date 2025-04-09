import tensorflow as tf
import numpy as np
import torch
import tifffile
from tqdm import trange
from torch.utils.data import Dataset
from patchify import unpatchify
import torchio
from sklearn import preprocessing
import onnxruntime

# list of classes for preprocessing and transforming images

class WholeVolumeDataset(Dataset):
    # this Dataset module accepts a list of raw image filenames and reads in the image one at a time

    def __init__(self, 
                 raw_directory = [],
                 raw_img = None, 
                 mask_directory = [], 
                 num_classes = None, 
                 raw_transform = None, 
                 label_transform = None, 
                 mask_order = (0,4,1,2,3), 
                 device = "cpu"):

        self.raw_img_list = raw_directory
        self.raw_img = raw_img
        self.mask_list = mask_directory
        self.num_classes = num_classes
        self.raw_transform = raw_transform
        self.label_transform = label_transform
        self.mask_order = mask_order
        self.device = device

    def __len__(self):
        return self.raw_img.shape[0]

    def __getitem__(self, idx):

        # Read and process a single 2D slice from the 3D raw image
        print(f"Reading slice {idx} from the volume")
        image = self.raw_img[idx, :, :].astype(np.float16)  # Select the Z-slice (Y, X)

        if self.raw_transform:
            image = self.raw_transform(image)
            image = torch.FloatTensor(image).to(self.device)
            image = torch.unsqueeze(image, dim=0)  # Add the channel dimension

        if self.mask_list:
            print("Reading Mask from list")
            # Load corresponding 2D mask slice if available
            mask = tifffile.imread(self.mask_list[idx]).astype(np.float16)
            if self.label_transform:
                mask = self.label_transform(mask)

            mask = torch.FloatTensor(to_categorical(mask, self.num_classes)).to(self.device)
            mask = torch.unsqueeze(mask, 0)  # Add the channel dimension
            mask = torch.permute(mask, self.mask_order)
        else:
            mask = None

        return image, mask

class MinMaxScalerVectorized(object):
    # def __call__(self,tensor):
    #     dist = (tensor.max() - tensor.min())
    #     dist[dist==0.0] = 1.0
    #     scale = 1.0 / dist
    #     tensor.mul_(scale).sub_(tensor.min())
    #     return tensor
    
    def __call__(self, array):
        return normalize(array)
    

class process_masks(object):
    def __init__(self, exp = '+s +d +f', ignore_starting_from = 3):
        # exp or experiment = 's+f+d' or 'f+d'() or 'f+d+af', where s = soma; f = filopodia; d = dendrite
        self.ignore_starting_from = ignore_starting_from
        self.exp = exp
    def __call__(self, array):
        # assuming the axon is labeled, make it a dendrite (2)
        axon_idx_z,axon_idx_x,axon_idx_y = np.where(array == 4)
        array[axon_idx_z,axon_idx_x,axon_idx_y] = 2

        if self.exp == '+s +d +f': # train model to segment soma, dendrite, and filopodias (semantic segmentation)
            idx_z,idx_x,idx_y = np.where(array > self.ignore_starting_from)
            array[idx_z,idx_x,idx_y] = 0 # make everything else 0
            return array

        if self.exp == '-s +d -f': # train model to detect background vs foreground (binary segmentation)
            soma_idx_z,soma_idx_x,soma_idx_y = np.where(array == 2)
            array[soma_idx_z,soma_idx_x,soma_idx_y] = 1 # change dendrites to soma (vice versa)

            filo_idx_z,filo_idx_x,filo_idx_y = np.where(array == 3) 
            array[filo_idx_z,filo_idx_x,filo_idx_y] = 1 # change filopodias to soma

            idx_z,idx_x,idx_y = np.where(array > self.ignore_starting_from)
            array[idx_z,idx_x,idx_y] = 0 # make everything else 0

            return array
        
        if self.exp == '+s +d -f': # Yes soma, Yes dendrite, No filopodia (merge filopodia to dendrite)
            filo_idx_z,filo_idx_x,filo_idx_y = np.where(array == 3)
            array[filo_idx_z,filo_idx_x,filo_idx_y] = 2

            idx_z,idx_x,idx_y = np.where(array > self.ignore_starting_from)
            array[idx_z,idx_x,idx_y] = 0 # make everything else 0
            return array

       

def to_categorical(y, num_classes):
    """ 1-hot encodes a tensor """
    return np.eye(num_classes, dtype='int16')[y.astype(np.int16)]

def normalize(input_image):
    input_image = input_image/input_image.max()
    return input_image

class new_shape(object):
    def __init__(self, new_xy = (600,960)):
        # new_xy: tuple(new y dimension, new x dimension). Example (600, 960)
        self.new_xy = new_xy
        
    def __call__(self, array):
        return place_into_center(array, self.new_xy)

def place_into_center(input_img, new_xy):
    # input_img = ndarray of size (z,y,x)
    
    # set up limits
    input_z_shape = input_img.shape[0]
    input_y_shape = input_img.shape[1]
    input_x_shape = input_img.shape[2]
    output_img = np.empty((input_z_shape, new_xy[0], new_xy[1]))
    
    # find the center of x direction
    new_x_half = np.uint16(new_xy[0]//2)
    new_y_half = np.uint16(new_xy[1]//2)
    
    old_x_half = np.uint16(input_x_shape//2)
    old_y_half = np.uint16(input_y_shape//2)
    
    output_img[:,new_x_half-old_x_half:new_x_half+old_x_half,new_y_half-old_y_half:new_y_half+old_y_half] = input_img
    return output_img

    

def reconstruct_training_masks(upper, lower, upper_size, lower_size, patch_size, orig_shape):
    
    # Reconstruct the image from batches (Batches, Channel, D, W, H)
    # upper: Tensor representing an image that is evenly split in the z-direction Tensor(Batches, D, W, H)
    # lower: Tensor representing an image that is leftover from the split in the z-direction Tensor(Batches, D, W, H)    
    # upper_size: Tensor representing the original shape of the split image in the form (z_loc, y_loc, x_loc, z_patch, y_patch, x_patch)
    # lower_size: Tensor representing the original shape of the split image in the form (z_loc, y_loc, x_loc, z_patch, y_patch, x_patch)
    # patch_size: Tensor representing the size of the subvolumes in the form Tensor(z_subsize, y_subsize, x_subsize)
    # orig_shape: the original shape of the input image (depth, height, width)
    
    # Batched data should not have the one-hot encoding
    
    if lower == None: 
        # reshape the predicted image
        steps_dim = list(steps_dim)
        upper_voxels = list(upper.shape[0:3]) # get subvolume location
        predicted_upper = torch.FloatTensor(predicted_upper).to(device)
        predicted_upper_reshaped = torch.reshape(predicted_upper, upper.shape)
        
        upper_unpatched = unpatchify(upper_img, to_upper_shape)

        return predicted_upper

    else:
        patch_size = list(patch_size)
        upper_size = list(upper_size)
        lower_size = list(lower_size)
        
        # reshape batches (B, D, H, W) to voxelized (z_loc, y_loc, x_loc, z_patch, y_patch, x_patch)
#         upper = torch.cat(upper)
#         lower = torch.cat(lower)
        
        upper = torch.reshape(upper, upper_size)
        lower = torch.reshape(lower, lower_size)
        
        # get the original size
        to_upper_shape = [a*b for a,b in zip(patch_size, upper_size)]
        to_lower_shape = [a*b for a,b in zip(patch_size, lower_size)]
        
        # release the image from the device

        upper = upper.cpu().detach().numpy()
        lower = lower.cpu().detach().numpy()
        
        reconstructed_upper = unpatchify(upper, to_upper_shape)
        reconstructed_lower = unpatchify(lower, to_lower_shape)
        
        # Merge inferenced quotient and remainder arrays
        z_patch = patch_size[0]
        quot, remain = divmod(orig_shape[0],z_patch)
        shift_up = reconstructed_lower.shape[0]-remain # get the number of layers to shift up
        merged = np.zeros(orig_shape) # Make an array for predicted values
        merged[0:reconstructed_upper.shape[0],...] = reconstructed_upper # copy upper
        merged[(reconstructed_upper.shape[0]-shift_up):,...] = reconstructed_lower # shift the lower up and merge with upper
        
        return merged
    

def to_numpy(tensor):
    return tensor.detach().cpu().numpy() if tensor.requires_grad else tensor.cpu().numpy()

def to_torch(np_arr):
    return torch.FloatTensor(np.array(np_arr))

