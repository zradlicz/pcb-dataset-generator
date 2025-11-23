#!/bin/bash
#SBATCH --job-name=pcb_dataset
#SBATCH --output=logs/slurm_%A_%a.out
#SBATCH --error=logs/slurm_%A_%a.err
#SBATCH --array=0-999                # Generate 1000 samples (adjust as needed)
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=01:00:00
#SBATCH --partition=gpu              # Use GPU partition if available (optional)

# SLURM Array Job for PCB Dataset Generation
# Each task generates one sample using its SLURM_ARRAY_TASK_ID

# Load required modules (adjust for your HPC environment)
module load singularity

# Configuration
CONTAINER_IMAGE="pcb-dataset.sif"
DATA_DIR="/scratch/$USER/pcb_data"
CONFIG_DIR="$DATA_DIR/config"
OUTPUT_DIR="$DATA_DIR/output"

# Ensure output directory exists
mkdir -p "$OUTPUT_DIR/logs"

# Get sample ID from array task ID
SAMPLE_ID=$SLURM_ARRAY_TASK_ID

echo "=========================================="
echo "SLURM Array Job: PCB Dataset Generation"
echo "=========================================="
echo "Job ID: $SLURM_JOB_ID"
echo "Array Task ID: $SLURM_ARRAY_TASK_ID"
echo "Sample ID: $SAMPLE_ID"
echo "Node: $SLURMD_NODENAME"
echo "CPUs: $SLURM_CPUS_PER_TASK"
echo "Memory: ${SLURM_MEM_PER_NODE}MB"
echo "=========================================="

# Run container with Singularity
singularity exec \
    --nv \
    --bind "$DATA_DIR:/data" \
    "$CONTAINER_IMAGE" \
    python3 /app/scripts/generate_single.py \
        --sample-id "$SAMPLE_ID" \
        --output-dir /data \
        --config-dir "$CONFIG_DIR" \
        --log-level INFO

# Capture exit code
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "Sample $SAMPLE_ID completed successfully"
else
    echo "Sample $SAMPLE_ID failed with exit code $EXIT_CODE"
fi

exit $EXIT_CODE
