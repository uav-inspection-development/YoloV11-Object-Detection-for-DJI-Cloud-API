# System Dependencies Installation Guide

This document explains how to install system dependencies for the YOLOv11 Solar Panel Detection project.

## Quick Start

### Automated Installation (Recommended)

For Ubuntu/Debian systems, use the provided script:

```bash
chmod +x install_system_deps.sh
./install_system_deps.sh
```

This script will:
- Detect your Ubuntu version
- Install appropriate OpenCV and OpenGL dependencies
- Handle package conflicts gracefully
- Provide fallbacks for older Ubuntu versions

### Manual Installation

If you prefer to install manually or are using a different system:

#### Ubuntu 22.04+ (Current LTS)

```bash
sudo apt-get update
sudo apt-get install -y \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgtk-3-0 \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    libv4l-dev \
    libxvidcore-dev \
    libx264-dev \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    libatlas-base-dev \
    python3-dev \
    python3-numpy \
    libgl1-mesa-dev \
    libgles2-mesa-dev
```

#### Ubuntu 20.04 (Older LTS)

```bash
sudo apt-get update
sudo apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgtk-3-0 \
    python3-dev \
    python3-numpy
```

#### Other Linux Distributions

- **CentOS/RHEL**: Use `yum` or `dnf` with equivalent package names
- **Arch Linux**: Use `pacman` with equivalent package names
- **Alpine**: Use `apk` with equivalent package names

#### Windows

System dependencies are typically handled by the Python packages themselves on Windows. You may need:
- Visual C++ Redistributable
- CUDA toolkit (if using GPU)

#### macOS

```bash
# Using Homebrew
brew install opencv
```

## Troubleshooting

### Common Issues

1. **Package not found**: Some packages may have different names on different Ubuntu versions
2. **Permission denied**: Make sure to use `sudo` for system package installation
3. **OpenGL issues**: If you encounter OpenGL-related errors, try installing both mesa packages

### GitHub Actions

The project's CI/CD pipeline automatically handles system dependencies using the `install_system_deps.sh` script.

### Docker

If you're using Docker, add this to your Dockerfile:

```dockerfile
# Copy and run system dependencies installer
COPY install_system_deps.sh /tmp/
RUN chmod +x /tmp/install_system_deps.sh && /tmp/install_system_deps.sh
```

## Verification

After installing system dependencies, verify the installation:

```bash
# Run the project validator
python tests/validate_config.py

# Test Python imports
python -c "import cv2; print(f'OpenCV version: {cv2.__version__}')"
```

## Getting Help

If you encounter issues:

1. Check the script output for specific error messages
2. Try the manual installation steps for your system
3. Open an issue with your system details and error logs
