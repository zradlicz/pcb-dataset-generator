#!/bin/bash
#SBATCH --job-name=pcb_gpu_render
#SBATCH --output=logs/gpu_render_%A_%a.out
#SBATCH --error=logs/gpu_render_%A_%a.err
#SBATCH --array=0-499                # Adjust based on num-samples
#SBATCH --cpus-per-task=8            # Fewer CPUs needed, GPU does the work
#SBATCH --mem=32G                    # Memory for BlenderProc
#SBATCH --time=01:00:00              # 1 hour - rendering is fast on GPU
#SBATCH --partition=msigpu           # GPU partition
#SBATCH --gres=gpu:h100:1            # Request 1 H100 GPU (overridden by submit script)
# NOTE: --constraint removed - GPU type is set by submit_split_pipeline.py --gpu-type flag
#SBATCH --tmp=20G                    # Request 20GB local scratch for Blender cache

# SLURM Array Job for PCB Dataset Generation - GPU Rendering Only
# This script runs steps 5-7: rendering, PNG extraction, format conversion
# Input: .blend files from CPU preprocessing
# Output: HDF5 files with RGB, depth, segmentation

# Configuration (set via command line or environment variables)
CONTAINER_IMAGE="${CONTAINER_IMAGE:-pcb-dataset-generator_latest.sif}"
DATA_DIR="${DATA_DIR:-/scratch/$USER/pcb_data}"
CONFIG_DIR="${CONFIG_DIR:-$DATA_DIR/config}"
BLENDER_CACHE_DIR="${BLENDER_CACHE_DIR:-$DATA_DIR/blender_cache}"
START_ID="${START_ID:-0}"

# Ensure output directory exists
mkdir -p "$DATA_DIR/logs"
mkdir -p "$DATA_DIR/output"
mkdir -p "$BLENDER_CACHE_DIR"

# Get sample ID from array task ID
SAMPLE_ID=$((START_ID + SLURM_ARRAY_TASK_ID))

echo "=========================================="
echo "PCB GPU Rendering (Steps 5-7)"
echo "=========================================="
echo "Job ID: $SLURM_JOB_ID"
echo "Array Task ID: $SLURM_ARRAY_TASK_ID"
echo "Sample ID: $SAMPLE_ID"
echo "Node: $SLURMD_NODENAME"
echo "CPUs: $SLURM_CPUS_PER_TASK"
echo "Memory: ${SLURM_MEM_PER_NODE}MB"
echo "GPU: $(nvidia-smi --query-gpu=name --format=csv,noheader)"
echo "Local Scratch: $TMPDIR"
echo "=========================================="

# Verify .blend file exists
BLEND_FILE="$DATA_DIR/renders/sample_$(printf '%06d' $SAMPLE_ID).blend"
if [ ! -f "$BLEND_FILE" ]; then
    echo "❌ ERROR: .blend file not found: $BLEND_FILE"
    echo "   Run CPU preprocessing first (cpu_preprocessing_array.sh)"
    exit 1
fi

echo "Input: $BLEND_FILE"

# Run GPU rendering in container
apptainer exec --nv \
    --bind "$DATA_DIR:/data" \
    --bind "$CONFIG_DIR:/app/config:ro" \
    --bind "$BLENDER_CACHE_DIR:/root/.cache/cycles" \
    --bind "$TMPDIR:/tmp" \
    "$CONTAINER_IMAGE" \
    python3 /app/scripts/render_from_intermediate.py \
        --num-samples 1 \
        --start-id "$SAMPLE_ID" \
        --input-dir /data/renders \
        --output-dir /data/output \
        --config-dir /app/config \
        --log-level INFO

# Capture exit code
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Sample $SAMPLE_ID rendering completed successfully"
    echo "   Output: $DATA_DIR/output/sample_$(printf '%06d' $SAMPLE_ID)_*.hdf5"
else
    echo "❌ Sample $SAMPLE_ID rendering failed with exit code $EXIT_CODE"
fi

exit $EXIT_CODE
