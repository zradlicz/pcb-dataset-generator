# ML Training Notebooks

This directory contains Jupyter notebooks for training machine learning models on the generated PCB dataset.

## Structure

```
notebooks/
├── README.md                          # This file
├── pcb_segmentation_training.ipynb    # Main training notebook
├── requirements.txt                   # Python dependencies for training
├── assets/                            # Plots, visualizations, figures
└── models/                            # Trained model checkpoints
```

## Getting Started

### Local Development

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Launch Jupyter**:
   ```bash
   jupyter notebook pcb_segmentation_training.ipynb
   ```

3. **Configure dataset path** in the notebook to point to your HDF5 files

### Google Colab

1. **Upload notebook to Colab**:
   - Go to [Google Colab](https://colab.research.google.com/)
   - Upload `pcb_segmentation_training.ipynb`

2. **Enable GPU**:
   - Runtime → Change runtime type → GPU

3. **Install dependencies** (first cell will handle this)

4. **Download dataset** (follow instructions in notebook)

## Dataset Format

The notebook expects HDF5 files from the PCB dataset generator with:
- **RGB images**: `colors` dataset (H x W x 3)
- **Segmentation masks**: `category_id_segmaps` dataset (H x W)
  - 0 = background
  - 1 = metal components
  - 2 = non-metal components
- **Depth maps**: `depth` dataset (H x W)
- **Instance masks**: `instance_segmaps`, `material_segmaps`, `name_segmaps`

## Training Task

**Binary segmentation**: Classify each pixel as metal (1) vs non-metal (2) component

**Potential architectures**:
- U-Net (classic, lightweight)
- DeepLabV3+ (state-of-the-art, heavier)
- Custom lightweight CNN

**Metrics**:
- IoU (Intersection over Union)
- Pixel accuracy
- Dice coefficient
- Per-class precision/recall

## Notes

- This is a **standalone component** separate from the dataset generation pipeline
- Models will be manually implemented (not AI-generated)
- Results should demonstrate dataset utility for PCB component segmentation
