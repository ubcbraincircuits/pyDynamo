
# import machine learning modules
import torch
import os
import numpy as np

from torchvision import transforms, utils
from torch.utils.data import DataLoader
from monai.networks.nets import UNet
from monai.inferers.inferer import SliceInferer

from pydynamo_brain.ui.actions.unet import processingFunctions


def modelPredict(image, mode="Soma+Dendrite", spatial_dim=2):
    path = os.getcwd()
    model_path = os.path.join(os.path.dirname(__file__), f'models/2D_{mode}.pth')
    # currently lateral steps are fixed as 512 due to the model being trained on full slices of 512x512.
    checkpoint = torch.load(model_path, map_location=torch.device('cpu'))
    lateral_steps = 512
    patch_size = (lateral_steps, lateral_steps)
    batch_size = 1
    input_chnl = 1
    output_chnl = 4
    norm_type = "batch"
    dropout = 0.1

    model = UNet(spatial_dims=2, 
                in_channels = input_chnl,
                out_channels = output_chnl,
                channels = (32, 64, 128, 256, 512),
                strides=(2, 2, 2, 2),
                num_res_units=2,
                norm = norm_type,
                dropout = dropout)

    model.load_state_dict(checkpoint['model_state_dict'])
    model = model.to("cpu")
    inferer = SliceInferer(roi_size=patch_size, sw_batch_size=batch_size, spatial_dim = 0, progress = True)

    raw_transform = transforms.Compose([processingFunctions.MinMaxScalerVectorized()])
    processed_img_dataset = processingFunctions.WholeVolumeDataset(raw_img=image,
                                        raw_transform=raw_transform)
    
    processed_img, _ = next(iter(processed_img_dataset))
    processed_img = torch.unsqueeze(processed_img, dim = 0)

    with torch.no_grad():
        output = inferer(inputs = processed_img, network=model)
        probabilities = torch.softmax(output,1)
        pred = processingFunctions.to_numpy(torch.argmax(probabilities, 1)).astype(np.int16)

    # soma category is inferenced for only "Neuron" => change all the soma labels (1) to dendrite labels (2)
    if len(np.unique(pred)) == 2:
        pred[pred==1] = 2
        return pred, len(np.unique(pred))+1
    else:
        return pred, len(np.unique(pred))