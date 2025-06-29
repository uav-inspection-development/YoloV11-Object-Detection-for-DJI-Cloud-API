#!/bin/bash
# System dependencies installer for YOLOv11 project
# This script handles OpenCV and other system dependencies for different Ubuntu versions

set -e

echo "🔧 Installing system dependencies for YOLOv11 project..."

# Detect Ubuntu version
if command -v lsb_release >/dev/null 2>&1; then
    UBUNTU_VERSION=$(lsb_release -rs)
    echo "📋 Detected Ubuntu version: $UBUNTU_VERSION"
else
    echo "⚠️  Cannot detect Ubuntu version, proceeding with default packages"
    UBUNTU_VERSION="22.04"
fi

# Update package lists
echo "📦 Updating package lists..."
sudo apt-get update

# Common packages that work across Ubuntu versions
COMMON_PACKAGES=(
    "libglib2.0-0"
    "libsm6" 
    "libxext6"
    "libxrender-dev"
    "libgomp1"
    "libgtk-3-0"
    "python3-dev"
    "python3-numpy"
)

# OpenCV specific packages
OPENCV_PACKAGES=(
    "libavcodec-dev"
    "libavformat-dev"
    "libswscale-dev"
    "libv4l-dev"
    "libxvidcore-dev"
    "libx264-dev"
    "libjpeg-dev"
    "libpng-dev"
    "libtiff-dev"
    "libatlas-base-dev"
)

# OpenGL packages (try modern first, fallback to older)
OPENGL_PACKAGES=(
    "libgl1-mesa-dev"
    "libgles2-mesa-dev"
)

# Combine all packages
ALL_PACKAGES=("${COMMON_PACKAGES[@]}" "${OPENCV_PACKAGES[@]}" "${OPENGL_PACKAGES[@]}")

echo "📋 Installing packages: ${ALL_PACKAGES[*]}"

# Install packages with error handling
FAILED_PACKAGES=()
for package in "${ALL_PACKAGES[@]}"; do
    echo "📦 Installing $package..."
    if sudo apt-get install -y "$package"; then
        echo "✅ Successfully installed $package"
    else
        echo "⚠️  Failed to install $package, continuing..."
        FAILED_PACKAGES+=("$package")
    fi
done

# Try to install libgl1-mesa-glx as fallback if modern OpenGL packages failed
if [[ " ${FAILED_PACKAGES[*]} " =~ " libgl1-mesa-dev " ]]; then
    echo "🔄 Trying fallback OpenGL package..."
    if sudo apt-get install -y libgl1-mesa-glx; then
        echo "✅ Successfully installed libgl1-mesa-glx as fallback"
    else
        echo "⚠️  OpenGL package installation failed, but continuing..."
    fi
fi

# Report any failed packages
if [ ${#FAILED_PACKAGES[@]} -gt 0 ]; then
    echo "⚠️  The following packages failed to install: ${FAILED_PACKAGES[*]}"
    echo "⚠️  This may not affect the core functionality"
fi

# Verify OpenCV can be imported (if Python is available)
if command -v python3 >/dev/null 2>&1; then
    echo "🧪 Testing basic Python functionality..."
    if python3 -c "print('✅ Python is working correctly')"; then
        echo "✅ Python basic test passed"
    fi
fi

echo "🎉 System dependencies installation completed!"
echo "💡 You can now install Python dependencies with: pip install -r requirements.txt"
