# PCB Dataset Generator - Production Plan

## Overview

Production-ready pipeline for generating machine learning datasets of realistic PCB images with segmentation ground truth. Built from proof-of-concept learnings, designed for HPC cluster deployment with SLURM.

---

## Architecture

### Design Principles

1. **Modular Design** - Each pipeline step is an independent, testable module
2. **Configuration-Driven** - YAML configs for all parameters, no hardcoded values
3. **Containerized** - Docker/Singularity for reproducible execution
4. **HPC-Ready** - Headless operation, SLURM array jobs, parallel generation
5. **Scalable** - Generate thousands of high-resolution samples efficiently

### Project Structure

```
pcb-dataset-generator/
├── Dockerfile                    # All dependencies (KiCad, Blender, Python)
├── docker-compose.yml           # Local testing
├── pyproject.toml               # Python package definition (uv-compatible)
├── README.md
├── PRODUCTION_PLAN.md           # This file
│
├── config/
│   ├── placement.yaml           # Perlin noise + component parameters
│   ├── render.yaml              # Camera positions + lighting
│   └── pipeline.yaml            # High-level orchestration
│
├── src/
│   └── pcb_dataset/
│       ├── __init__.py
│       ├── placement.py         # Perlin noise component placement logic
│       ├── board.py             # KiCad board creation
│       ├── exporter.py          # .pcb3d export via kicad-cli + pcb2blender
│       ├── importer.py          # Blender import via pcb2blender
│       ├── renderer.py          # BlenderProc with segmentation
│       ├── converter.py         # HDF5 → COCO/PNG export
│       ├── pipeline.py          # Orchestrates full workflow
│       └── utils/
│           ├── config.py        # YAML config loading
│           ├── logging.py       # Structured logging
│           ├── paths.py         # Path management
│           └── validation.py    # File validation helpers
│
├── scripts/
│   ├── generate_single.py       # CLI: Generate 1 sample
│   ├── generate_batch.py        # CLI: Generate N samples locally
│   └── slurm/
│       ├── array_job.sh         # SLURM array job script
│       └── submit.py            # Python wrapper to submit jobs
│
├── tests/
│   ├── test_placement.py
│   ├── test_board.py
│   ├── test_exporter.py
│   ├── test_renderer.py
│   └── test_pipeline.py
│
├── pcb2blender/                 # Git submodule (vendored dependency)
│
└── data/                        # Container mount point
    ├── boards/                  # Generated .kicad_pcb files
    ├── pcb3d/                   # Exported .pcb3d files
    ├── renders/                 # .blend files
    ├── output/                  # Final HDF5/COCO outputs
    └── logs/                    # Execution logs
```

---

## Pipeline Modules

### 1. Component Placement (`placement.py`)

**Purpose**: Generate organic component layouts using Perlin noise clustering algorithm.

**Configuration**: `config/placement.yaml`

```yaml
perlin:
  scale: 30.0              # Noise scale factor
  octaves: 4               # Noise detail levels
  persistence: 0.5         # Amplitude decay per octave
  lacunarity: 2.0          # Frequency increase per octave
  seed: null               # Random seed (null = random)

vignette:
  enabled: true            # Edge density falloff
  strength: 0.7            # Falloff strength

components:
  small:
    count: 100             # Number of small components
    spacing: 2.0           # Minimum spacing (mm)
  medium:
    count: 30
    spacing: 5.0
  large:
    count: 18
    spacing: 8.0

board:
  width: 100.0             # Board width (mm)
  height: 100.0            # Board height (mm)
```

**Key Functions**:
- `PerlinPlacer.generate_placements()` → List[ComponentPlacement]
- Returns x, y, rotation, size category, component type for each component

**POC Learnings**:
- Perlin noise creates realistic organic clustering
- Vignette effect prevents edge overcrowding
- 148 components achieved in POC with good density

---

### 2. Board Creation (`board.py`)

**Purpose**: Create KiCad PCB files from component placements.

**Configuration**: None (uses placement output)

**Key Functions**:
- `BoardCreator.create_board(placements, output_path, board_name)` → Path
- Creates `.kicad_pcb` file with components, traces, soldermask, test points

**POC Learnings**:
- Use KiCad Python API (`pcbnew`) for board manipulation
- ComponentLibrary class manages component lookup
- Auto-routing connects all pins
- Soldermask layer critical for realistic appearance

---

### 3. PCB Export (`exporter.py`)

**Purpose**: Export `.kicad_pcb` to `.pcb3d` format for Blender import.

**Configuration**: None

**Key Functions**:
- `PCB3DExporter.export(kicad_pcb_path, output_pcb3d_path)` → Path

**Critical POC Learnings** ⚠️:
1. **Use kicad-cli for VRML export** - GUI `pcbnew.ExportVRML()` doesn't work headless
   ```bash
   kicad-cli pcb export vrml --units m --user-origin 0x0mm input.kicad_pcb
   ```
2. **Units MUST be meters** - `--units m` (Blender interprets VRML as meters)
3. **Set origin explicitly** - `--user-origin 0x0mm` prevents solder pad offset
4. **Use real pcb2blender code** - Don't reimplement, use official source via git submodule

**Implementation**:
- Step 1: Export VRML using `kicad-cli` subprocess
- Step 2: Convert VRML to `.pcb3d` using pcb2blender exporter code
- Validate output file size and structure

---

### 4. Blender Import (`importer.py`)

**Purpose**: Import `.pcb3d` files into Blender scenes.

**Configuration**: None

**Key Functions**:
- `BlenderImporter.import_pcb3d(pcb3d_path, output_blend_path)` → Path
- Runs in Blender subprocess: `blender --background --python import_script.py`

**POC Learnings**:
- Use real pcb2blender importer code from `pcb2blender/pcb2blender_importer/`
- Works in headless mode (no GUI required)
- Imports components, traces, solder pads, materials correctly

---

### 5. Rendering (`renderer.py`)

**Purpose**: Render photorealistic images with segmentation masks using BlenderProc.

**Configuration**: `config/render.yaml`

```yaml
cameras:
  - position: [0.0, 0.0, 0.3]
    rotation: [0.0, 0.0, 0.0]    # Euler angles (radians)

lighting:
  sun:
    energy: 2.0
    location: [0, 0, 1.0]
    rotation: [0, 0, 0]

  fill_lights:
    - location: [0.3, 0.3, 0.5]
      energy: 0.6
    - location: [-0.3, 0.3, 0.5]
      energy: 0.6
    - location: [0.3, -0.3, 0.5]
      energy: 0.6
    - location: [-0.3, -0.3, 0.5]
      energy: 0.6

background:
  color: [0.8, 0.8, 0.8]

resolution: 2048
```

**Key Functions**:
- `BProcRenderer.render(blend_path, output_dir)` → Path
- Outputs HDF5 with RGB, depth, segmentation maps

**Critical POC Learnings** ⚠️:

**Segmentation Strategy**:
1. **Material-based detection** - Inspect Mat4cad BSDF shader nodes
2. **Multi-material object splitting** - Separate objects by material for per-face segmentation
3. **Category assignments**:
   - Category 1 (Metal/Probable): Solder joints, component pins/leads, exposed copper, test points
   - Category 2 (Non-metal): Component plastic/ceramic bodies, soldermask

**Implementation Details**:
```python
# Material detection via Mat4cad inspection
for node in material.node_tree.nodes:
    if 'mat4cad' in node.name.lower():
        if 'mat_base' in node.keys():
            if node['mat_base'] == 2:  # 2 = metal surface
                material['category_id'] = 1
        # Also check node group name
        if 'metal' in node.node_tree.name.lower():
            material['category_id'] = 1
        elif 'plastic' in node.node_tree.name.lower():
            material['category_id'] = 2

# Split multi-material objects for per-face segmentation
for obj in objects:
    if len(unique_materials) > 1:
        bpy.ops.mesh.separate(type='MATERIAL')

# BlenderProc segmentation output
bproc.renderer.enable_segmentation_output(
    map_by=["category_id", "material", "instance", "name"],
    default_values={'category_id': 0, 'material': None}
)
```

**Results from POC**:
- 755 metal/probable objects detected
- 145 non-metal objects detected
- 30 component types successfully split
- Segmentation maps: category_id, material, instance, name

**Known Limitation**:
- PCB substrate currently shows as all metal (copper + soldermask together)
- Future enhancement: texture-based splitting for copper vs soldermask

---

### 6. Format Conversion (`converter.py`)

**Purpose**: Convert HDF5 output to standard ML formats (COCO, PNG).

**Configuration**: None

**Key Functions**:
- `FormatConverter.hdf5_to_coco(hdf5_path, output_dir)` - Future implementation
- `FormatConverter.extract_images(hdf5_path, output_dir)` - Extract as separate PNGs

**Notes**:
- HDF5 is BlenderProc's native format (efficient, bundled)
- Most ML frameworks prefer COCO JSON + PNG images
- Converter enables compatibility with Detectron2, MMDetection, YOLO, etc.

---

### 7. Pipeline Orchestration (`pipeline.py`)

**Purpose**: Coordinate full workflow from placement to final output.

**Configuration**: `config/pipeline.yaml`

```yaml
dataset:
  num_samples: 1000
  output_format: hdf5        # hdf5, coco, both

resolutions:
  - 512
  - 1024
  - 2048

seed:
  base: 42
  auto_increment: true       # Each sample: base + sample_id

paths:
  boards: boards/
  pcb3d: pcb3d/
  renders: renders/
  output: output/
  logs: logs/

cleanup:
  keep_boards: false
  keep_pcb3d: false
  keep_blend: false
```

**Key Functions**:
- `Pipeline.generate_sample(sample_id)` → Path
  1. Generate placements
  2. Create KiCad board
  3. Export to .pcb3d
  4. Import to Blender (subprocess)
  5. Render with segmentation (subprocess)
  6. Convert format (if requested)
  7. Cleanup intermediate files

**Subprocess Execution**:
- Blender operations run in separate processes:
  - Import: `blender --background --python import_script.py -- <args>`
  - Render: `blenderproc run renderer.py <args>`

---

## HPC Deployment (SLURM)

### Container Strategy

**Format**: Singularity/Apptainer (HPC-standard container runtime)

**Build**:
```bash
# Build Docker image locally
docker build -t pcb-dataset:latest .

# Convert to Singularity image
singularity build pcb-dataset.sif docker-daemon://pcb-dataset:latest
```

### SLURM Array Jobs

**Concept**: Generate N samples in parallel using SLURM job arrays.

**Example**: Generate 1000 samples
- Submit 1 array job with 1000 tasks (0-999)
- Each task generates 1 sample with unique sample_id
- Results written to shared filesystem

**Job Script** (`scripts/slurm/array_job.sh`):
```bash
#!/bin/bash
#SBATCH --job-name=pcb_dataset
#SBATCH --output=logs/slurm_%A_%a.out
#SBATCH --error=logs/slurm_%A_%a.err
#SBATCH --array=0-999
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=01:00:00
#SBATCH --partition=gpu

module load singularity

singularity exec \
    --nv \
    --bind /scratch/$USER/pcb_data:/data \
    pcb-dataset.sif \
    python /app/scripts/generate_single.py \
        --sample-id $SLURM_ARRAY_TASK_ID \
        --output-dir /data/output \
        --config-dir /data/config
```

**Submission**:
```bash
# Copy configs to scratch space
cp -r config /scratch/$USER/pcb_data/

# Submit job
python scripts/slurm/submit.py --num-samples 1000 --config-dir /scratch/$USER/pcb_data/config
```

### Resource Requirements (per sample)

- **CPU**: 4 cores (Blender rendering can use multiple cores)
- **Memory**: 16GB (high-res rendering + BlenderProc)
- **GPU**: Optional but recommended (faster rendering)
- **Time**: ~30-60 minutes per sample (depends on complexity)
- **Storage**: ~500MB per sample (HDF5 output)

### Data Management

**Filesystem Layout**:
```
/scratch/$USER/pcb_data/
├── config/              # Input: YAML configurations
├── output/              # Output: Generated datasets
│   ├── sample_0000.hdf5
│   ├── sample_0001.hdf5
│   └── ...
└── logs/                # SLURM logs
    ├── slurm_12345_0.out
    └── ...
```

**Post-Processing**:
- Validate all samples completed successfully
- Convert to COCO format (if needed)
- Split into train/val/test sets
- Generate dataset statistics
- Archive to permanent storage

---

## Dependencies

### System Dependencies

- **KiCad 8.0+** - PCB design software with Python API
- **Blender 4.5+** - 3D modeling and rendering (not 5.0, compatibility issues)
- **BlenderProc 2.x** - Blender automation library
- **kicad-cli** - Command-line KiCad tools (headless export)

### Python Dependencies

```toml
[project]
dependencies = [
    "numpy>=1.24.0",
    "pyyaml>=6.0",
    "h5py>=3.8.0",
    "blenderproc>=2.5.0",
    "opencv-python>=4.8.0",
    "pillow>=10.0.0",
]
```

### Vendored Dependencies

- **pcb2blender** - Git submodule (official KiCad to Blender exporter/importer)
  - Repository: https://github.com/antmicro/pcb2blender
  - Used for: VRML to .pcb3d conversion, Blender import
  - **Critical**: Must initialize submodules (`git submodule update --init --recursive`)

---

## Testing Strategy

### Unit Tests

- `tests/test_placement.py` - Perlin noise generation, component placement logic
- `tests/test_board.py` - KiCad board creation, validation
- `tests/test_exporter.py` - .pcb3d export, file structure validation
- `tests/test_renderer.py` - Segmentation logic, material detection

### Integration Tests

- End-to-end pipeline test (1 sample)
- Validate all intermediate files can be opened in respective applications
- Verify segmentation accuracy on known boards

### CI/CD Considerations

- **Headless mode required** - All tests must run without GUI
- **Mock objects** - For components requiring KiCad/Blender installation
- **Pre-built fixtures** - Sample boards, expected outputs for validation
- **Container testing** - Run tests inside Docker to match HPC environment

---

## Implementation Phases

### Phase 1: Core Infrastructure ✅ COMPLETE

- [x] Project structure
- [x] Configuration system (YAML-based)
- [x] Docker container (built and tested)
- [x] Core modules (placement, board, exporter, importer, renderer)
- [x] Basic pipeline orchestration
- [x] **POC Code Ported**: All modules successfully ported from proof-of-concept
  - [x] `board.py` - KiCad board creation with ComponentLibrary
  - [x] `exporter.py` - .pcb3d export with kicad-cli integration
  - [x] `importer.py` - Blender import via pcb2blender
  - [x] `renderer.py` - BlenderProc with full segmentation logic
  - [x] Blender subprocess scripts (import + render)
  - [x] Pipeline orchestration complete
- [x] Git submodule integration (pcb2blender from 30350n/pcb2blender)

**Status**: Ready for Phase 2 testing

### Phase 2: Testing & Validation (IN PROGRESS)

- [ ] Unit tests for each module
- [x] Integration test (single sample end-to-end) ✅
- [x] GPU acceleration configured and tested ✅
- [ ] Manual validation in KiCad/Blender
- [ ] Segmentation accuracy verification
- [ ] Performance benchmarking

**Target**: Verify pipeline generates valid outputs

**Progress (2025-11-24)**:
- ✅ End-to-end pipeline tested successfully with GPU
- ✅ Docker container with NVIDIA GPU support configured
- ✅ BlenderProc rendering with OPTIX GPU acceleration
- ✅ Generated first test sample (148 components, 512x512, 32 samples)
- ⚠️ Some warnings observed (detailed below)

### Phase 3: HPC Deployment

- [ ] Singularity image build from Docker
- [ ] SLURM job scripts testing
- [ ] Test on HPC cluster (small batch: 10 samples)
- [ ] Performance profiling and optimization
- [ ] Resource usage analysis (CPU, memory, time per sample)

**Target**: Achieve stable HPC batch generation

### Phase 4: Production Dataset Generation

- [ ] Generate full dataset (1000+ samples)
- [ ] Format conversion to COCO (optional)
- [ ] Dataset validation and statistics
- [ ] Train/val/test split
- [ ] Documentation and archival
- [ ] ML model training verification

**Target**: Production-ready dataset for ML training

---

## Key Learnings from POC

### Technical Decisions

✅ **Use Official Source Code**
- Prefer real pcb2blender over custom implementations
- Avoids bugs, easier to maintain

✅ **CLI Tools Over API When Needed**
- `kicad-cli pcb export vrml` works headless
- `pcbnew.ExportVRML()` requires GUI context

✅ **Unit Conversion Critical**
- KiCad: millimeters
- Blender VRML: meters
- Must use `--units m` flag

✅ **Material-based Segmentation**
- Mat4cad `mat_base` property: 0=plastic, 2=metal
- Multi-material object splitting enables per-face segmentation

✅ **GPU Acceleration** (Added 2025-11-24)
- NVIDIA Container Toolkit required for Docker GPU access
- BlenderProc GPU rendering: `set_render_devices(desired_gpu_device_type='OPTIX')`
- Cycles device must be set: `bpy.context.scene.cycles.device = 'GPU'`
- Massive speedup: ~50 seconds (GPU) vs 5+ minutes (CPU) for 512x512@32samples
- Test GPU access: `docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi`

### Debugging Approach

1. **Manual GUI Testing First** - Validate tools work before automating
2. **Validate at Each Stage** - Check file sizes, structures, contents
3. **Start Simple, Add Complexity** - POC → Production incrementally

---

## Success Criteria

### Module-Level
- Each module has unit tests with >80% coverage
- Integration test passes for single sample
- All intermediate files validated in target applications

### Pipeline-Level
- Generate 1000 samples successfully
- <5% failure rate on HPC cluster
- Segmentation accuracy validated on sample set

### Dataset-Level
- HDF5 outputs contain all required data (RGB, depth, 4 segmentation maps)
- COCO format export works correctly
- Dataset statistics generated (class distribution, etc.)
- Ready for ML training pipeline

---

## Future Enhancements

1. **PCB Layer Separation** - Texture-based splitting for copper vs soldermask
2. **COCO Export** - Direct export to COCO format with bounding boxes
3. **Randomization** - Soldermask colors, lighting variations, camera angles
4. **Visualization Tools** - Overlay segmentation masks on RGB for debugging
5. **Dataset Augmentation** - Realistic backgrounds, camera noise, defects
6. **Component Variety** - Expand component library for more diversity

---

## Contact & Support

For issues, questions, or contributions, refer to:
- Project README.md
- POC repository: `/home/zach/code/pcb-pipeline/`
- Documentation: This file (PRODUCTION_PLAN.md)

---

## Current Status Summary

**Phase**: Phase 2 Testing & Validation (IN PROGRESS)

**Completed (2025-11-23)**:
- ✅ Full production project structure created
- ✅ All POC code successfully ported to modular architecture
- ✅ Docker container built with KiCad 8.0, Blender 4.2, BlenderProc
- ✅ Git repository initialized with pcb2blender submodule
- ✅ Configuration system implemented (3 YAML files)
- ✅ CLI scripts and SLURM deployment ready
- ✅ Python package installable via uv/pip

**Completed (2025-11-24)**:
- ✅ **GPU acceleration configured and tested**
  - NVIDIA Container Toolkit installed
  - Docker GPU passthrough with `--gpus all` flag
  - BlenderProc OPTIX rendering enabled
  - RTX 4060 GPU successfully utilized
- ✅ **First end-to-end pipeline test successful**
  - Generated sample with 148 components
  - KiCad board creation: 3 seconds
  - .pcb3d export: 1 second
  - Blender import: 8 seconds
  - BlenderProc rendering (512x512@32samples): ~50 seconds
  - Total pipeline time: ~1 minute

**Known Issues** (2025-11-24):
- ⚠️ Some pip warnings during BlenderProc setup (cosmetic, not blocking)
- ⚠️ KiCad action plugin assertion warnings (non-fatal)
- 🔴 **CRITICAL: No copper traces/routing** - Board only has footprints, no traces
  - `board.py` missing trace generation code
  - Need to implement auto-routing or programmatic trace placement
  - ✅ **POC HAS WORKING EXAMPLE**: `/home/zach/code/pcb-pipeline/` has trace generation
- 🔴 **CRITICAL: No 3D models assigned to footprints**
  - Footprints placed but 3D models not linked
  - Need to add model assignment in `_place_component()`
  - ✅ **POC HAS WORKING EXAMPLE**: `/home/zach/code/pcb-pipeline/` has 3D model assignment
- 🔴 **Component overlap apparent** - Likely due to missing 3D models
  - Footprints may overlap because 3D visualization doesn't show actual component size
  - Collision detection exists in placement code, but may need tuning
  - ✅ **POC HAS WORKING EXAMPLE**: Check POC placement for reference
- ⚠️ **Segmentation affected** - Missing traces and 3D models lead to poor segmentation

**IMPORTANT NOTE**: The POC repository at `/home/zach/code/pcb-pipeline/` contains working implementations of all missing features. Reference these scripts when implementing fixes:
- 3D model assignment
- Copper trace generation
- Proper component spacing/collision detection
- Full segmentation pipeline

**Setup Instructions**:
```bash
# One-time setup: Install NVIDIA Container Toolkit
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
  sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Build and test
docker build -t pcb-dataset:latest .
bash scripts/test_container.sh
```

**Next Milestone** (Updated 2025-11-24):
Priority 1 - Fix Critical Issues:
- [ ] Add 3D model assignment to footprints in `board.py`
- [ ] Implement copper trace/routing generation
- [ ] Fix/verify component spacing and collision detection
- [ ] Re-test pipeline with fixes

Priority 2 - Validation:
- [ ] Manual validation of generated outputs (KiCad, Blender)
- [ ] Verify segmentation quality with proper traces and 3D models
- [ ] Performance benchmarking with different settings

---

**Last Updated**: 2025-11-24
**Status**: Phase 2 - Testing & Validation (IN PROGRESS - GPU working!)
