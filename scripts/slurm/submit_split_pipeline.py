#!/usr/bin/env python3
"""
Submit split CPU/GPU pipeline to SLURM for optimized HPC execution.

This script submits two SLURM array jobs:
1. CPU preprocessing (steps 1-4): Generate .blend files
2. GPU rendering (steps 5-7): Render final outputs (depends on CPU job)

Usage:
    python scripts/slurm/submit_split_pipeline.py --num-samples 1000 --gpu-type h100
"""

import argparse
import subprocess
import sys
from pathlib import Path
import re


def submit_cpu_preprocessing(
    num_samples: int,
    start_id: int,
    container_image: Path,
    data_dir: Path,
    config_dir: Path,
    cpus: int = 16,
    mem_gb: int = 32,
    time: str = "02:00:00",
    partition: str = "msismall",
    scratch_gb: int = 50,
):
    """
    Submit CPU preprocessing array job.

    Returns:
        Job ID of submitted job
    """
    job_script = Path(__file__).parent / "cpu_preprocessing_array.sh"

    cmd = [
        "sbatch",
        f"--array=0-{num_samples-1}",
        f"--cpus-per-task={cpus}",
        f"--mem={mem_gb}G",
        f"--time={time}",
        f"--partition={partition}",
        f"--tmp={scratch_gb}G",
        f"--export=ALL,CONTAINER_IMAGE={container_image},DATA_DIR={data_dir},CONFIG_DIR={config_dir},START_ID={start_id}",
        str(job_script),
    ]

    print("=" * 70)
    print("Submitting CPU Preprocessing Job (Steps 1-4)")
    print("=" * 70)
    print(f"  Samples: {num_samples} (IDs {start_id} to {start_id + num_samples - 1})")
    print(f"  Partition: {partition}")
    print(f"  Resources: {cpus} CPUs, {mem_gb}GB RAM, {scratch_gb}GB scratch")
    print(f"  Walltime: {time}")
    print(f"  Container: {container_image}")
    print(f"  Data dir: {data_dir}")
    print(f"  Config dir: {config_dir}")
    print()

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        # Extract job ID from output like "Submitted batch job 12345"
        match = re.search(r"Submitted batch job (\d+)", result.stdout)
        if match:
            job_id = match.group(1)
            print(f"✅ CPU preprocessing job submitted successfully!")
            print(f"   Job ID: {job_id}")
            print()
            return job_id
        else:
            print(f"⚠️  Job submitted but couldn't parse job ID")
            print(f"   Output: {result.stdout}")
            return None
    else:
        print(f"❌ Job submission failed!")
        print(f"   Error: {result.stderr}")
        sys.exit(1)


def submit_gpu_rendering(
    num_samples: int,
    start_id: int,
    container_image: Path,
    data_dir: Path,
    config_dir: Path,
    blender_cache_dir: Path,
    gpu_type: str = "h100",
    dependency_job_id: str = None,
    cpus: int = 8,
    mem_gb: int = 32,
    time: str = "01:00:00",
    partition: str = "msigpu",
    scratch_gb: int = 20,
):
    """
    Submit GPU rendering array job.

    Args:
        dependency_job_id: If provided, this job will only start after the dependency completes

    Returns:
        Job ID of submitted job
    """
    job_script = Path(__file__).parent / "gpu_rendering_array.sh"

    cmd = [
        "sbatch",
        f"--array=0-{num_samples-1}",
        f"--cpus-per-task={cpus}",
        f"--mem={mem_gb}G",
        f"--time={time}",
        f"--partition={partition}",
        f"--gres=gpu:{gpu_type}:1",
        f"--tmp={scratch_gb}G",
    ]

    # Add dependency if CPU job ID provided
    if dependency_job_id:
        cmd.append(f"--dependency=afterok:{dependency_job_id}")

    cmd.extend([
        f"--export=ALL,CONTAINER_IMAGE={container_image},DATA_DIR={data_dir},CONFIG_DIR={config_dir},BLENDER_CACHE_DIR={blender_cache_dir},START_ID={start_id}",
        str(job_script),
    ])

    print("=" * 70)
    print("Submitting GPU Rendering Job (Steps 5-7)")
    print("=" * 70)
    print(f"  Samples: {num_samples} (IDs {start_id} to {start_id + num_samples - 1})")
    print(f"  Partition: {partition}")
    print(f"  GPU Type: {gpu_type}")
    print(f"  Resources: {cpus} CPUs, {mem_gb}GB RAM, {scratch_gb}GB scratch")
    print(f"  Walltime: {time}")
    if dependency_job_id:
        print(f"  Dependency: afterok:{dependency_job_id} (waits for CPU job)")
    print(f"  Container: {container_image}")
    print(f"  Data dir: {data_dir}")
    print(f"  Config dir: {config_dir}")
    print()

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        # Extract job ID from output
        match = re.search(r"Submitted batch job (\d+)", result.stdout)
        if match:
            job_id = match.group(1)
            print(f"✅ GPU rendering job submitted successfully!")
            print(f"   Job ID: {job_id}")
            print()
            return job_id
        else:
            print(f"⚠️  Job submitted but couldn't parse job ID")
            print(f"   Output: {result.stdout}")
            return None
    else:
        print(f"❌ Job submission failed!")
        print(f"   Error: {result.stderr}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Submit split CPU/GPU pipeline to SLURM for optimized HPC execution"
    )

    # Required arguments
    parser.add_argument("--num-samples", type=int, required=True, help="Number of samples to generate")

    # Optional arguments
    parser.add_argument("--start-id", type=int, default=0, help="Starting sample ID (default: 0)")
    parser.add_argument(
        "--container-image",
        type=Path,
        default=Path("pcb-dataset-generator_latest.sif"),
        help="Path to Apptainer/Singularity container image",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path(f"/scratch/{Path.home().name}/pcb_data"),
        help="Data directory in scratch space",
    )
    parser.add_argument(
        "--config-dir",
        type=Path,
        default=None,
        help="Configuration directory (default: DATA_DIR/config)",
    )
    parser.add_argument(
        "--gpu-type",
        type=str,
        choices=["h100", "a100", "a40", "l40s", "v100"],
        default="h100",
        help="GPU type to request (default: h100)",
    )
    parser.add_argument(
        "--cpu-only",
        action="store_true",
        help="Only submit CPU preprocessing job (useful for testing)",
    )
    parser.add_argument(
        "--gpu-only",
        action="store_true",
        help="Only submit GPU rendering job (assumes .blend files exist)",
    )

    # Resource arguments for CPU job
    parser.add_argument("--cpu-cpus", type=int, default=16, help="CPUs for CPU job (default: 16)")
    parser.add_argument("--cpu-mem", type=int, default=32, help="Memory (GB) for CPU job (default: 32)")
    parser.add_argument(
        "--cpu-time", type=str, default="02:00:00", help="Walltime for CPU job (default: 02:00:00)"
    )
    parser.add_argument(
        "--cpu-partition", type=str, default="msismall", help="Partition for CPU job (default: msismall)"
    )

    # Resource arguments for GPU job
    parser.add_argument("--gpu-cpus", type=int, default=8, help="CPUs for GPU job (default: 8)")
    parser.add_argument("--gpu-mem", type=int, default=32, help="Memory (GB) for GPU job (default: 32)")
    parser.add_argument(
        "--gpu-time", type=str, default="01:00:00", help="Walltime for GPU job (default: 01:00:00)"
    )
    parser.add_argument(
        "--gpu-partition", type=str, default="msigpu", help="Partition for GPU job (default: msigpu)"
    )

    args = parser.parse_args()

    # Setup paths
    data_dir = args.data_dir.expanduser().resolve()
    config_dir = args.config_dir if args.config_dir else data_dir / "config"
    blender_cache_dir = data_dir / "blender_cache"
    container_image = args.container_image.expanduser().resolve()

    # Create directories
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "logs").mkdir(exist_ok=True)

    # Validate config directory
    if not config_dir.exists():
        print(f"❌ Error: Config directory not found: {config_dir}")
        print(f"   Copy your config files: cp -r config {config_dir}")
        sys.exit(1)

    # Validate container image
    if not container_image.exists():
        print(f"❌ Error: Container image not found: {container_image}")
        print(f"   Pull from Docker Hub:")
        print(f"   apptainer pull docker://yourusername/pcb-dataset-generator:latest")
        sys.exit(1)

    print()
    print("=" * 70)
    print("PCB Dataset Generator - Split CPU/GPU Pipeline Submission")
    print("=" * 70)
    print()

    cpu_job_id = None
    gpu_job_id = None

    # Submit CPU preprocessing job
    if not args.gpu_only:
        cpu_job_id = submit_cpu_preprocessing(
            num_samples=args.num_samples,
            start_id=args.start_id,
            container_image=container_image,
            data_dir=data_dir,
            config_dir=config_dir,
            cpus=args.cpu_cpus,
            mem_gb=args.cpu_mem,
            time=args.cpu_time,
            partition=args.cpu_partition,
        )

    # Submit GPU rendering job
    if not args.cpu_only:
        gpu_job_id = submit_gpu_rendering(
            num_samples=args.num_samples,
            start_id=args.start_id,
            container_image=container_image,
            data_dir=data_dir,
            config_dir=config_dir,
            blender_cache_dir=blender_cache_dir,
            gpu_type=args.gpu_type,
            dependency_job_id=cpu_job_id,  # GPU waits for CPU to finish
            cpus=args.gpu_cpus,
            mem_gb=args.gpu_mem,
            time=args.gpu_time,
            partition=args.gpu_partition,
        )

    # Summary
    print("=" * 70)
    print("Submission Complete!")
    print("=" * 70)
    if cpu_job_id:
        print(f"  CPU Job ID: {cpu_job_id}")
    if gpu_job_id:
        print(f"  GPU Job ID: {gpu_job_id}")
        if cpu_job_id:
            print(f"  (GPU job will start after CPU job completes)")
    print()
    print("Monitor jobs:")
    print(f"  squeue -u $USER")
    if cpu_job_id:
        print(f"  squeue -j {cpu_job_id}")
    if gpu_job_id:
        print(f"  squeue -j {gpu_job_id}")
    print()
    print("Check logs:")
    print(f"  tail -f {data_dir}/logs/cpu_prep_*.out")
    print(f"  tail -f {data_dir}/logs/gpu_render_*.out")
    print()
    print("Output location:")
    print(f"  .blend files: {data_dir}/renders/")
    print(f"  Final HDF5s: {data_dir}/output/")
    print("=" * 70)


if __name__ == "__main__":
    main()
