"""Project resource paths that work from source and PyInstaller builds."""

import os
import sys


def abs_path(relative_path, base_path=None, path_type="current"):
    """Resolve project-relative paths in source and directory-mode bundles."""
    if base_path is not None:
        return os.path.normpath(os.path.join(base_path, relative_path))

    if getattr(sys, "frozen", False):
        # PyInstaller stores --add-data files below _MEIPASS.
        root = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
        relative_path = relative_path.replace("\\", "/")
        while relative_path.startswith("../"):
            relative_path = relative_path[3:]
        return os.path.normpath(os.path.join(root, relative_path))

    # Source modules live in <project>/src and historically pass ../ paths.
    caller_dir = os.path.dirname(os.path.abspath(sys._getframe(1).f_code.co_filename))
    if path_type == "parent":
        caller_dir = os.path.dirname(caller_dir)
    return os.path.normpath(os.path.join(caller_dir, relative_path))
