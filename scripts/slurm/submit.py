#!/usr/bin/env python3
"""
Submit SLURM array job for PCB dataset generation.

Usage:
    python scripts/slurm/submit.py --num-samples 1000 --config-dir /scratch/$USER/pcb_data/config
"""

import argparse
import subprocess
import sys
from pathlib import Path


def submit_array_job(
    num_samples: int,
    config_dir: Path,
    container_image: Path,
    data_dir: Path,
    cpus: int = 4,
    mem_gb: int = 16,
    time: str = "01:00:00",
    partition: str = "gpu",
):
    """
    Submit SLURM array job.

    Args:
        num_samples: Number of samples to generate
        config_dir: Configuration directory
        container_image: Path to Singularity image
        data_dir: Data directory (scratch space)
        cpus: CPUs per task
        mem_gb: Memory per task (GB)
        time: Wall time limit (HH:MM:SS)
        partition: SLURM partition
    """
    # Ensure directories exist
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "logs").mkdir(exist_ok=True)

    # Validate config directory
    config_dir = Path(config_dir)
    if not config_dir.exists():
        print(f"Error: Config directory not found: {config_dir}")
        sys.exit(1)

    # Validate container image
    container_image = Path(container_image)
    if not container_image.exists():
        print(f"Error: Container image not found: {container_image}")
        print(f"Build it with: docker build -t pcb-dataset:latest .")
        print(f"               singularity build {container_image} docker-daemon://pcb-dataset:latest")
        sys.exit(1)

    # Submit job
    job_script = Path(__file__).parent / "array_job.sh"

    cmd = [
        "sbatch",
        f"--array=0-{num_samples-1}",
        f"--cpus-per-task={cpus}",
        f"--mem={mem_gb}G",
        f"--time={time}",
        f"--partition={partition}",
        str(job_script),
    ]

    print("Submitting SLURM array job...")
    print(f"  Samples: {num_samples}")
    print(f"  Config: {config_dir}")
    print(f"  Container: {container_image}")
    print(f"  Data dir: {data_dir}")
    print(f"  Resources: {cpus} CPUs, {mem_gb}GB, {time}")
    print(f"  Command: {' '.join(cmd)}")
    print()

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        job_id = result.stdout.strip().split()[-1]
        print(f"Job submitted successfully!")
        print(f"  Job ID: {job_id}")
        print()
        print(f"Monitor with:")
        print(f"  squeue -u $USER")
        print(f"  squeue -j {job_id}")
        print()
        print(f"Check logs:")
        print(f"  tail -f {data_dir}/logs/slurm_*.out")
    else:
        print(f"Job submission failed!")
        print(f"  Error: {result.stderr}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Submit SLURM array job for PCB dataset generation")

    parser.add_argument("--num-samples", type=int, required=True, help="Number of samples to generate")
    parser.add_argument(
        "--config-dir",
        type=Path,
        required=True,
        help="Configuration directory (must be in scratch space)",
    )
    parser.add_argument(
        "--container-image",
        type=Path,
        default=Path("pcb-dataset.sif"),
        help="Path to Singularity container image",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path(f"/scratch/{Path.home().name}/pcb_data"),
        help="Data directory (scratch space)",
    )
    parser.add_argument("--cpus", type=int, default=4, help="CPUs per task")
    parser.add_argument("--mem-gb", type=int, default=16, help="Memory per task (GB)")
    parser.add_argument("--time", type=str, default="01:00:00", help="Wall time limit (HH:MM:SS)")
    parser.add_argument("--partition", type=str, default="gpu", help="SLURM partition")

    args = parser.parse_args()

    submit_array_job(
        num_samples=args.num_samples,
        config_dir=args.config_dir,
        container_image=args.container_image,
        data_dir=args.data_dir,
        cpus=args.cpus,
        mem_gb=args.mem_gb,
        time=args.time,
        partition=args.partition,
    )


if __name__ == "__main__":
    main()
