#!/usr/bin/env python3
"""
Configuration file validator for the YOLOv11 project.
This script validates that all configuration files are properly formatted.
"""

import configparser
import sys
import os
from pathlib import Path

def validate_config_file(file_path: str, file_description: str) -> bool:
    """Validate a single configuration file."""
    try:
        if not os.path.exists(file_path):
            print(f"❌ {file_description} ({file_path}) does not exist")
            return False
        
        config = configparser.ConfigParser()
        config.read(file_path)
        print(f"✅ {file_description} ({file_path}) is valid")
        return True
    except Exception as e:
        print(f"❌ {file_description} ({file_path}) has errors: {e}")
        return False

def validate_file_exists(file_path: str, file_description: str) -> bool:
    """Check if a file exists."""
    if os.path.exists(file_path):
        print(f"✅ {file_description} ({file_path}) exists")
        return True
    else:
        print(f"❌ {file_description} ({file_path}) does not exist")
        return False

def main():
    """Main validation function."""
    print("🔍 Validating YOLOv11 project configuration files...")
    print("=" * 60)
    
    all_valid = True
    
    # Configuration files to validate
    config_files = [
        (".flake8", "Flake8 configuration"),
        ("mypy.ini", "MyPy configuration"),
        ("setup.cfg", "Setup configuration"),
    ]
    
    # Regular files to check
    regular_files = [
        ("requirements.txt", "Production requirements"),
        ("requirements-dev.txt", "Development requirements"),
        ("README.md", "README file"),
        ("LICENSE", "License file"),
        ("install_system_deps.sh", "System dependencies installer"),
    ]
    
    # Validate configuration files
    print("\n📝 Configuration files:")
    for file_path, description in config_files:
        if not validate_config_file(file_path, description):
            all_valid = False
    
    # Check regular files
    print("\n📄 Required files:")
    for file_path, description in regular_files:
        if not validate_file_exists(file_path, description):
            all_valid = False
    
    # Check directories
    print("\n📁 Required directories:")
    required_dirs = ["src", "tests", "weights", ".github/workflows"]
    for dir_path in required_dirs:
        if os.path.exists(dir_path):
            print(f"✅ Directory {dir_path} exists")
        else:
            print(f"❌ Directory {dir_path} does not exist")
            all_valid = False
    
    print("\n" + "=" * 60)
    if all_valid:
        print("🎉 All configuration files and required files are valid!")
        sys.exit(0)
    else:
        print("💥 Some configuration files or required files have issues!")
        sys.exit(1)

if __name__ == "__main__":
    main()
