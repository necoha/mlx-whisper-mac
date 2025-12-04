"""
Runtime hook for PyInstaller.
This runs BEFORE the main application and any imports.
Detects macOS version and replaces mlx libraries if needed.
"""
import os
import sys
import platform
import shutil

def get_macos_version():
    """Get macOS major version number."""
    try:
        version = platform.mac_ver()[0]  # e.g., "15.7.2" or "26.1"
        major = int(version.split('.')[0])
        return major
    except:
        return 15  # Default to macOS 15 if detection fails

def setup_mlx_libraries():
    """Replace mlx libraries based on macOS version."""
    if not getattr(sys, 'frozen', False):
        return
    
    bundle_dir = sys._MEIPASS
    macos_version = get_macos_version()
    
    # Only replace for macOS < 26
    if macos_version >= 26:
        return
    
    # Paths
    macos15_dir = os.path.join(bundle_dir, "macos15")
    if not os.path.exists(macos15_dir):
        return
    
    # Source files (macOS 15 compatible)
    src_metallib = os.path.join(macos15_dir, "mlx.metallib")
    src_libmlx = os.path.join(macos15_dir, "libmlx.dylib")
    
    # Target directories
    resources_mlx_lib = os.path.join(bundle_dir, "mlx", "lib")
    
    # The Frameworks directory is at ../../Frameworks relative to _MEIPASS (which is Resources)
    # _MEIPASS = .../Contents/Resources
    # Frameworks = .../Contents/Frameworks
    contents_dir = os.path.dirname(bundle_dir)
    frameworks_mlx_lib = os.path.join(contents_dir, "Frameworks", "mlx", "lib")
    
    # Replace metallib in Resources/mlx/lib
    if os.path.exists(src_metallib) and os.path.exists(resources_mlx_lib):
        target = os.path.join(resources_mlx_lib, "mlx.metallib")
        try:
            if os.path.exists(target) or os.path.islink(target):
                os.remove(target)
            shutil.copy2(src_metallib, target)
        except Exception as e:
            print(f"Warning: Could not replace metallib in Resources: {e}")
    
    # Replace libmlx.dylib in Frameworks/mlx/lib
    if os.path.exists(src_libmlx) and os.path.exists(frameworks_mlx_lib):
        target = os.path.join(frameworks_mlx_lib, "libmlx.dylib")
        try:
            if os.path.exists(target) or os.path.islink(target):
                os.remove(target)
            shutil.copy2(src_libmlx, target)
        except Exception as e:
            print(f"Warning: Could not replace libmlx in Frameworks: {e}")

# Execute on import (before main app starts)
setup_mlx_libraries()
