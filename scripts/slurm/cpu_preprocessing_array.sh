#!/bin/bash
#SBATCH --job-name=pcb_cpu_prep
#SBATCH --output=logs/cpu_prep_%A_%a.out
#SBATCH --error=logs/cpu_prep_%A_%a.err
#SBATCH --array=0-499                # Adjust based on num-samples
#SBATCH --cpus-per-task=16           # Use more CPUs for KiCad/Blender operations
#SBATCH --mem=32G                    # Higher memory for 3D model loading
#SBATCH --time=02:00:00              # 2 hours should be enough for preprocessing
#SBATCH --partition=msismall         # CPU-only partition with long walltime
#SBATCH --tmp=50G                    # Request 50GB local scratch storage

# SLURM Array Job for PCB Dataset Generation - CPU Preprocessing Only
# This script runs steps 1-4: placement, board creation, export, import
# Output: .blend files ready for GPU rendering

# Configuration (set via command line or environment variables)
CONTAINER_IMAGE="${CONTAINER_IMAGE:-pcb-dataset-generator_latest.sif}"
DATA_DIR="${DATA_DIR:-/scratch/$USER/pcb_data}"
CONFIG_DIR="${CONFIG_DIR:-$DATA_DIR/config}"
START_ID="${START_ID:-0}"

# Ensure output directory exists
mkdir -p "$DATA_DIR/logs"
mkdir -p "$DATA_DIR/renders"

# Get sample ID from array task ID
SAMPLE_ID=$((START_ID + SLURM_ARRAY_TASK_ID))

echo "=========================================="
echo "PCB CPU Preprocessing (Steps 1-4)"
echo "=========================================="
echo "Job ID: $SLURM_JOB_ID"
echo "Array Task ID: $SLURM_ARRAY_TASK_ID"
echo "Sample ID: $SAMPLE_ID"
echo "Node: $SLURMD_NODENAME"
echo "CPUs: $SLURM_CPUS_PER_TASK"
echo "Memory: ${SLURM_MEM_PER_NODE}MB"
echo "Local Scratch: $TMPDIR"
echo "=========================================="

# Run CPU preprocessing in container
apptainer exec \
    --bind "$DATA_DIR:/data" \
    --bind "$CONFIG_DIR:/app/config:ro" \
    --bind "$TMPDIR:/tmp" \
    "$CONTAINER_IMAGE" \
    python3 /app/scripts/generate_intermediate.py \
        --num-samples 1 \
        --start-id "$SAMPLE_ID" \
        --output-dir /data \
        --config-dir /app/config \
        --log-level INFO

# Capture exit code
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Sample $SAMPLE_ID preprocessing completed successfully"
    echo "   .blend file: $DATA_DIR/renders/sample_$(printf '%06d' $SAMPLE_ID).blend"
else
    echo "❌ Sample $SAMPLE_ID preprocessing failed with exit code $EXIT_CODE"
fi

exit $EXIT_CODE
