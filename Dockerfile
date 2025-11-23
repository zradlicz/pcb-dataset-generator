# PCB Dataset Generator - Production Container
# Based on Ubuntu with KiCad, Blender, and BlenderProc

FROM ubuntu:22.04

# Prevent interactive prompts during installation
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# Install system dependencies
RUN apt-get update && apt-get install -y \
    # Basic utilities
    wget \
    curl \
    git \
    ca-certificates \
    software-properties-common \
    # Python 3.10+
    python3.10 \
    python3.10-dev \
    python3-pip \
    # X11 libraries (needed for Blender headless)
    libx11-6 \
    libxi6 \
    libxxf86vm1 \
    libxfixes3 \
    libxrender1 \
    libgl1 \
    libglu1-mesa \
    libsm6 \
    # Additional Blender dependencies
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Add KiCad PPA and install KiCad 8.0+
RUN add-apt-repository --yes ppa:kicad/kicad-8.0-releases && \
    apt-get update && \
    apt-get install -y \
    kicad \
    kicad-libraries \
    && rm -rf /var/lib/apt/lists/*

# Install Blender 4.5 (download official binary)
# Note: Not using Blender 5.0 due to compatibility issues
ENV BLENDER_VERSION=4.2.3
ENV BLENDER_DIR=/opt/blender

RUN wget -q https://download.blender.org/release/Blender4.2/blender-${BLENDER_VERSION}-linux-x64.tar.xz && \
    tar -xf blender-${BLENDER_VERSION}-linux-x64.tar.xz -C /opt && \
    mv /opt/blender-${BLENDER_VERSION}-linux-x64 ${BLENDER_DIR} && \
    rm blender-${BLENDER_VERSION}-linux-x64.tar.xz && \
    ln -s ${BLENDER_DIR}/blender /usr/local/bin/blender

# Set up Python environment
RUN python3 -m pip install --upgrade pip setuptools wheel

# Install uv for fast dependency management
RUN pip install uv

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml ./
COPY src/ ./src/
COPY config/ ./config/
COPY scripts/ ./scripts/

# Install Python dependencies
# Note: BlenderProc and bpy are installed via pip, not uv (compatibility)
RUN pip install -e . && \
    pip install blenderproc

# Clone pcb2blender as a git submodule alternative (vendored)
# In production, this should be a git submodule, but for container we clone directly
RUN git clone --depth 1 https://github.com/antmicro/pcb2blender.git /app/pcb2blender && \
    cd /app/pcb2blender && \
    git submodule update --init --recursive

# Add pcb2blender to Python path
ENV PYTHONPATH="/app/pcb2blender:${PYTHONPATH}"

# Configure KiCad paths
ENV KICAD_PATH=/usr/share/kicad
ENV KICAD_SYMBOL_DIR=/usr/share/kicad/symbols
ENV KICAD_FOOTPRINT_DIR=/usr/share/kicad/footprints
ENV KICAD_3DMODEL_DIR=/usr/share/kicad/3dmodels

# Configure Blender for headless rendering
ENV BLENDER_USER_SCRIPTS=/root/.config/blender/4.2/scripts
ENV BLENDER_SYSTEM_SCRIPTS=${BLENDER_DIR}/4.2/scripts

# Create data mount point
RUN mkdir -p /data/{boards,pcb3d,renders,output,logs}

# Set up logging
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python3 -c "import sys; import bpy; import pcbnew" || exit 1

# Default command
CMD ["python3", "/app/scripts/generate_single.py", "--help"]
