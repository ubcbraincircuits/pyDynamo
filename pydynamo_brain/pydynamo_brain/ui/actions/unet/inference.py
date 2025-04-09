import torch
import numpy as np
import pathlib
from torchvision import transforms
from torch.utils.data import DataLoader
from monai.networks.nets import UNet
from monai.inferers import SliceInferer
from pydynamo_brain.ui.actions.unet import processingFunctions
from torch.cuda.amp import autocast

def modelPredict(image, mode, slice_batch_size=4):
    path = pathlib.Path(__file__).parent.resolve()
    model_path = f'{path}/models/2D_{mode}.pth'

    # Load checkpoint and model setup
    checkpoint = torch.load(model_path, map_location=torch.device('cpu'))
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    model = UNet(
        spatial_dims=2, 
        in_channels=1,
        out_channels=4,
        channels=(32, 64, 128, 256, 512),
        strides=(2, 2, 2, 2),
        num_res_units=2,
        norm="batch",
        dropout=0.1
    ).to(device)
    
    model.load_state_dict(checkpoint['model_state_dict'])
    model.eval()  # Set to evaluation mode

    # Initialize inferer with batch size
    inferer = SliceInferer(roi_size=(512, 512), sw_batch_size=slice_batch_size, spatial_dim=0, overlap=0.5, progress=True)

    # Transform and prepare the image for inference
    raw_transform = transforms.Compose([processingFunctions.MinMaxScalerVectorized()])
    processed_img_dataset = processingFunctions.WholeVolumeDataset(raw_img=image, raw_transform=raw_transform)

    # Use DataLoader for efficient loading
    data_loader = DataLoader(
        processed_img_dataset, 
        batch_size=slice_batch_size, 
        num_workers=4, 
        pin_memory=True,
        collate_fn=lambda x: torch.stack([item[0] for item in x], dim=0)  # Stack batch of slices
    )

    pred = np.zeros_like(image, dtype=np.int8)  # Initialize prediction array

    # Process batches of slices
    with torch.no_grad():
        for batch_idx, batch_data in enumerate(data_loader):
            batch_data = batch_data.unsqueeze(1).to(device)  # Add channel dimension
            with autocast(enabled=device.type == 'cuda'):
                output = inferer(inputs=batch_data, network=model)
                probabilities = torch.softmax(output, dim=1)
                pred_batch = processingFunctions.to_numpy(torch.argmax(probabilities, dim=1)).astype(np.int8)

            # Assign predictions to the corresponding slices in output volume
            start_idx = batch_idx * slice_batch_size
            for i, pred_slice in enumerate(pred_batch):
                pred[start_idx + i, :, :] = pred_slice

    # Post-processing for dendrite/soma labels
    unique_labels = np.unique(pred)
    if len(unique_labels) == 2:
        pred[pred == 1] = 2
        return pred, len(unique_labels) + 1
    else:
        return pred, len(unique_labels)
