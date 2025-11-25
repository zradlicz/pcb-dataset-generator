#!/bin/bash
# Test script for Docker container

echo "Testing PCB Dataset Generator Container"
echo "========================================"

# Create test output directory
mkdir -p data/test_output

echo ""
echo "Running container to generate a single sample..."
echo ""

docker run --rm \
    --gpus all \
    -v "$(pwd)/data:/data" \
    -v "$(pwd)/config:/app/config:ro" \
    pcb-dataset:latest \
    python3 /app/scripts/generate_single.py \
        --sample-id 0 \
        --output-dir /data/test_output \
        --config-dir /app/config \
        --log-level DEBUG

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "✓ Container test successful!"
    echo ""
    echo "Check output at: data/test_output/"
    ls -lh data/test_output/
else
    echo ""
    echo "✗ Container test failed with exit code: $EXIT_CODE"
    echo ""
    echo "Check logs at: data/test_output/logs/"
fi

exit $EXIT_CODE
