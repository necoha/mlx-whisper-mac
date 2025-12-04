"""
Runtime hook for PyInstaller.
This runs BEFORE the main application and any imports.
Detects macOS version and replaces mlx libraries if needed.
"""
import os
import sys
import platform
import shutil

def log(msg):
    """Write to stderr for debugging."""
    sys.stderr.write(f"[runtime_hook] {msg}\n")
    sys.stderr.flush()

def get_macos_version():
    """Get macOS major version number."""
    try:
        version = platform.mac_ver()[0]  # e.g., "15.7.2" or "26.1"
        major = int(version.split('.')[0])
        return major
    except:
        return 15  # Default to macOS 15 if detection fails

def find_mlx_lib_dirs(base_dir):
    """Find all directories containing mlx libraries."""
    mlx_dirs = []
    for root, dirs, files in os.walk(base_dir):
        if 'libmlx.dylib' in files or 'mlx.metallib' in files:
            mlx_dirs.append(root)
        # Also check for symlinks
        for f in files:
            if f in ('libmlx.dylib', 'mlx.metallib'):
                full_path = os.path.join(root, f)
                if os.path.islink(full_path):
                    mlx_dirs.append(root)
                    break
    return list(set(mlx_dirs))

def setup_mlx_libraries():
    """Replace mlx libraries based on macOS version."""
    if not getattr(sys, 'frozen', False):
        log("Not frozen, skipping")
        return
    
    macos_version = get_macos_version()
    log(f"macOS version: {macos_version}")
    
    # Only replace for macOS < 26
    if macos_version >= 26:
        log("macOS 26+, using bundled libraries")
        return
    
    log("macOS < 26, need to replace mlx libraries")
    
    # Get app bundle paths
    bundle_dir = sys._MEIPASS
    log(f"_MEIPASS: {bundle_dir}")
    
    # Find the app bundle root (.app/Contents)
    # _MEIPASS is typically .app/Contents/Frameworks or .app/Contents/Resources
    if 'Contents' in bundle_dir:
        contents_dir = bundle_dir
        while os.path.basename(contents_dir) != 'Contents' and contents_dir != '/':
            contents_dir = os.path.dirname(contents_dir)
    else:
        contents_dir = os.path.dirname(bundle_dir)
    
    log(f"Contents dir: {contents_dir}")
    
    # Look for macos15 directory in multiple locations
    possible_macos15_dirs = [
        os.path.join(bundle_dir, "macos15"),
        os.path.join(contents_dir, "Resources", "macos15"),
        os.path.join(contents_dir, "Frameworks", "macos15"),
    ]
    
    macos15_dir = None
    for d in possible_macos15_dirs:
        log(f"Checking: {d} exists={os.path.exists(d)}")
        if os.path.exists(d):
            macos15_dir = d
            break
    
    if not macos15_dir:
        log("ERROR: macos15 directory not found!")
        # List what's in _MEIPASS
        try:
            log(f"Contents of _MEIPASS: {os.listdir(bundle_dir)[:20]}...")
        except Exception as e:
            log(f"Could not list _MEIPASS: {e}")
        return
    
    log(f"Found macos15 dir: {macos15_dir}")
    
    # Source files (macOS 15 compatible)
    src_metallib = os.path.join(macos15_dir, "mlx.metallib")
    src_libmlx = os.path.join(macos15_dir, "libmlx.dylib")
    
    log(f"src_metallib exists: {os.path.exists(src_metallib)}")
    log(f"src_libmlx exists: {os.path.exists(src_libmlx)}")
    
    if not os.path.exists(src_metallib) or not os.path.exists(src_libmlx):
        log("ERROR: Source files not found in macos15 directory!")
        return
    
    # Find all mlx lib directories in the bundle
    mlx_dirs = find_mlx_lib_dirs(contents_dir)
    log(f"Found mlx lib dirs: {mlx_dirs}")
    
    # Also check common locations
    common_mlx_paths = [
        os.path.join(contents_dir, "Resources", "mlx", "lib"),
        os.path.join(contents_dir, "Frameworks", "mlx", "lib"),
        os.path.join(bundle_dir, "mlx", "lib"),
    ]
    for p in common_mlx_paths:
        if os.path.exists(p) and p not in mlx_dirs:
            mlx_dirs.append(p)
    
    # Replace files in all found directories
    replaced_count = 0
    for mlx_dir in mlx_dirs:
        log(f"Processing: {mlx_dir}")
        
        # Replace metallib
        target_metallib = os.path.join(mlx_dir, "mlx.metallib")
        if os.path.exists(target_metallib) or os.path.islink(target_metallib):
            try:
                os.remove(target_metallib)
                shutil.copy2(src_metallib, target_metallib)
                log(f"  Replaced metallib: {target_metallib}")
                replaced_count += 1
            except Exception as e:
                log(f"  ERROR replacing metallib: {e}")
        
        # Replace libmlx
        target_libmlx = os.path.join(mlx_dir, "libmlx.dylib")
        if os.path.exists(target_libmlx) or os.path.islink(target_libmlx):
            try:
                os.remove(target_libmlx)
                shutil.copy2(src_libmlx, target_libmlx)
                log(f"  Replaced libmlx: {target_libmlx}")
                replaced_count += 1
            except Exception as e:
                log(f"  ERROR replacing libmlx: {e}")
    
    log(f"Replacement complete. {replaced_count} files replaced.")

# Execute on import (before main app starts)
setup_mlx_libraries()
