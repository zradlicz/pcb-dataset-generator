# PCB Dataset Generator

Production-ready pipeline for generating machine learning datasets of realistic PCB images with segmentation ground truth.

## Features

- **Organic Component Placement**: Perlin noise-based clustering for realistic layouts
- **Automated PCB Generation**: KiCad Python API for programmatic board creation
- **Photorealistic Rendering**: BlenderProc with physically-based materials
- **Segmentation Ground Truth**: Material-based segmentation (metal vs non-metal parts)
- **HPC-Ready**: Containerized, SLURM-compatible for cluster deployment
- **Scalable**: Generate thousands of high-resolution samples in parallel

## Quick Start

### Local Development

1. **Setup environment**:
   ```bash
   uv venv venv
   source venv/bin/activate
   uv pip install -e .
   ```

2. **Initialize pcb2blender submodule**:
   ```bash
   git submodule update --init --recursive
   ```

3. **Configure pipeline**:
   Edit YAML files in `config/`:
   - `placement.yaml` - Component placement parameters
   - `render.yaml` - Camera and lighting settings
   - `pipeline.yaml` - Dataset generation settings

4. **Generate single sample**:
   ```bash
   python scripts/generate_single.py --sample-id 0 --output-dir data/output
   ```

5. **Generate batch locally**:
   ```bash
   python scripts/generate_batch.py --num-samples 10 --output-dir data/output
   ```

### Docker

1. **Build container**:
   ```bash
   docker build -t pcb-dataset:latest .
   ```

2. **Run**:
   ```bash
   docker run -v $(pwd)/data:/data pcb-dataset:latest \
       python /app/scripts/generate_single.py --sample-id 0 --output-dir /data/output
   ```

### HPC Cluster (SLURM)

1. **Build Singularity image**:
   ```bash
   singularity build pcb-dataset.sif docker-daemon://pcb-dataset:latest
   ```

2. **Copy configs to scratch**:
   ```bash
   cp -r config /scratch/$USER/pcb_data/
   ```

3. **Submit array job**:
   ```bash
   python scripts/slurm/submit.py --num-samples 1000 --config-dir /scratch/$USER/pcb_data/config
   ```

## Architecture

The pipeline consists of 7 modular stages:

1. **Component Placement** (`placement.py`) - Perlin noise-based organic layouts
2. **Board Creation** (`board.py`) - KiCad PCB file generation
3. **PCB Export** (`exporter.py`) - .pcb3d format export via kicad-cli
4. **Blender Import** (`importer.py`) - Import .pcb3d into Blender scenes
5. **Rendering** (`renderer.py`) - BlenderProc photorealistic rendering + segmentation
6. **Format Conversion** (`converter.py`) - HDF5 → COCO/PNG export
7. **Pipeline Orchestration** (`pipeline.py`) - End-to-end workflow coordination

See [PRODUCTION_PLAN.md](PRODUCTION_PLAN.md) for detailed architecture documentation.

## Output Format

Each sample generates:

- **RGB Image**: Photorealistic render (512x512, 1024x1024, or 2048x2048)
- **Depth Map**: Per-pixel depth values
- **Segmentation Maps**:
  - `category_id`: Metal (1) vs Non-metal (2) semantic segmentation
  - `material`: Per-material segmentation
  - `instance`: Instance segmentation (separate objects of same class)
  - `name`: Per-object segmentation

Default format: **HDF5** (all data in one file)
Optional: **COCO JSON + PNG** (for ML framework compatibility)

## Configuration

### Component Placement (`config/placement.yaml`)

```yaml
perlin:
  scale: 30.0              # Noise scale
  octaves: 4               # Detail levels
  persistence: 0.5
  lacunarity: 2.0
  seed: null               # null = random

components:
  small:
    count: 100             # Number of components
    spacing: 2.0           # Minimum spacing (mm)
  medium:
    count: 30
    spacing: 5.0
  large:
    count: 18
    spacing: 8.0

board:
  width: 100.0             # mm
  height: 100.0
```

### Rendering (`config/render.yaml`)

```yaml
cameras:
  - position: [0.0, 0.0, 0.3]
    rotation: [0.0, 0.0, 0.0]

lighting:
  sun:
    energy: 2.0
  fill_lights:
    - location: [0.3, 0.3, 0.5]
      energy: 0.6

resolution: 2048
```

### Pipeline (`config/pipeline.yaml`)

```yaml
dataset:
  num_samples: 1000
  output_format: hdf5      # hdf5, coco, both

resolutions:
  - 512
  - 1024
  - 2048

seed:
  base: 42
  auto_increment: true
```

## Requirements

- **KiCad 8.0+** (with kicad-cli)
- **Blender 4.5+** (not 5.0 - compatibility issues)
- **BlenderProc 2.x**
- **Python 3.10+**
- **Docker** (for containerization)
- **Singularity/Apptainer** (for HPC deployment)

## Development

### Project Structure

```
pcb-dataset-generator/
├── src/pcb_dataset/       # Core library modules
├── scripts/               # CLI scripts
├── config/                # YAML configurations
├── tests/                 # Unit and integration tests
├── data/                  # Generated data (gitignored)
└── pcb2blender/           # Git submodule
```

### Running Tests

```bash
pytest tests/
```

### Adding Component Types

Edit the component library in `src/pcb_dataset/board.py`:

```python
class ComponentLibrary:
    def __init__(self):
        self.components = {
            'small': ['resistor', 'capacitor', 'led'],
            'medium': ['ic_8pin', 'diode'],
            'large': ['ic_32pin', 'connector']
        }
```

## Troubleshooting

### VRML Export Fails
- Ensure `kicad-cli` is in PATH
- Check KiCad version (8.0+ required)

### Blender Import Errors
- Initialize git submodules: `git submodule update --init --recursive`
- Verify Blender version (4.5+, not 5.0)

### Segmentation Shows All Metal
- This is expected for PCB substrate (known limitation)
- Component metal/plastic parts should segment correctly

### HPC Job Fails
- Check SLURM logs in `data/logs/slurm_*.err`
- Verify Singularity image built correctly
- Ensure scratch filesystem has sufficient space

## Citation

If you use this dataset generator in your research, please cite:

```bibtex
@software{pcb_dataset_generator,
  title = {PCB Dataset Generator},
  author = {Your Name},
  year = {2025},
  url = {https://github.com/yourusername/pcb-dataset-generator}
}
```

## License

[Your chosen license]

## Acknowledgments

- **pcb2blender**: https://github.com/antmicro/pcb2blender
- **BlenderProc**: https://github.com/DLR-RM/BlenderProc
- **KiCad**: https://www.kicad.org/
