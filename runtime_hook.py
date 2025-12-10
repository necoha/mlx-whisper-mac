"""
Runtime hook for PyInstaller.
This runs BEFORE the main application and any imports.
Detects macOS version and replaces mlx package if needed.
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

def setup_mlx_libraries():
    """Replace entire mlx package based on macOS version."""
    if not getattr(sys, 'frozen', False):
        log("Not frozen, skipping")
        return
    
    macos_version = get_macos_version()
    log(f"macOS version: {macos_version}")
    
    # Only replace for macOS < 26
    if macos_version >= 26:
        log("macOS 26+, using bundled libraries")
        return
    
    log("macOS < 26, need to replace mlx package")
    
    # Get app bundle paths
    bundle_dir = sys._MEIPASS
    log(f"_MEIPASS: {bundle_dir}")
    
    # Find the app bundle root (.app/Contents)
    if 'Contents' in bundle_dir:
        contents_dir = bundle_dir
        while os.path.basename(contents_dir) != 'Contents' and contents_dir != '/':
            contents_dir = os.path.dirname(contents_dir)
    else:
        contents_dir = os.path.dirname(bundle_dir)
    
    log(f"Contents dir: {contents_dir}")
    
    # Look for macos15_mlx directory (contains complete mlx package for macOS 15)
    possible_macos15_dirs = [
        os.path.join(bundle_dir, "macos15_mlx"),
        os.path.join(contents_dir, "Resources", "macos15_mlx"),
        os.path.join(contents_dir, "Frameworks", "macos15_mlx"),
    ]
    
    macos15_mlx_dir = None
    for d in possible_macos15_dirs:
        log(f"Checking: {d} exists={os.path.exists(d)}")
        if os.path.exists(d):
            macos15_mlx_dir = d
            break
    
    if not macos15_mlx_dir:
        log("ERROR: macos15_mlx directory not found!")
        try:
            log(f"Contents of _MEIPASS: {os.listdir(bundle_dir)[:30]}...")
        except Exception as e:
            log(f"Could not list _MEIPASS: {e}")
        return
    
    log(f"Found macos15_mlx dir: {macos15_mlx_dir}")
    
    # Source mlx directory (complete macOS 15 compatible mlx package)
    src_mlx_dir = os.path.join(macos15_mlx_dir, "mlx")
    if not os.path.exists(src_mlx_dir):
        log(f"ERROR: mlx directory not found in {macos15_mlx_dir}")
        return
    
    log(f"Source mlx dir: {src_mlx_dir}")
    
    # List contents of source mlx dir for debugging
    try:
        src_contents = os.listdir(src_mlx_dir)
        log(f"Source mlx contents: {src_contents}")
        src_lib_dir = os.path.join(src_mlx_dir, "lib")
        if os.path.exists(src_lib_dir):
            log(f"Source lib contents: {os.listdir(src_lib_dir)}")
    except Exception as e:
        log(f"Could not list source dir: {e}")
    
    # Find target mlx directories in the bundle
    target_mlx_dirs = []
    for base in [contents_dir, bundle_dir]:
        for root, dirs, files in os.walk(base):
            if os.path.basename(root) == 'mlx' and 'core.cpython-312-darwin.so' in files:
                target_mlx_dirs.append(root)
    
    # Also check common locations
    common_paths = [
        os.path.join(contents_dir, "Frameworks", "mlx"),
        os.path.join(contents_dir, "Resources", "mlx"),
        os.path.join(bundle_dir, "mlx"),
    ]
    for p in common_paths:
        if os.path.exists(p) and p not in target_mlx_dirs:
            target_mlx_dirs.append(p)
    
    log(f"Found target mlx dirs: {target_mlx_dirs}")
    
    # Replace files in each target directory
    replaced_count = 0
    for target_dir in target_mlx_dirs:
        log(f"Processing target: {target_dir}")
        
        # Key files to replace
        files_to_replace = [
            ("core.cpython-312-darwin.so", "core.cpython-312-darwin.so"),
            ("lib/libmlx.dylib", "lib/libmlx.dylib"),
            ("lib/mlx.metallib", "lib/mlx.metallib"),
        ]
        
        for src_rel, target_rel in files_to_replace:
            src_file = os.path.join(src_mlx_dir, src_rel)
            target_file = os.path.join(target_dir, target_rel)
            
            if not os.path.exists(src_file):
                log(f"  Source not found: {src_file}")
                continue
            
            if os.path.exists(target_file) or os.path.islink(target_file):
                try:
                    os.remove(target_file)
                    shutil.copy2(src_file, target_file)
                    log(f"  Replaced: {target_rel}")
                    replaced_count += 1
                except Exception as e:
                    log(f"  ERROR replacing {target_rel}: {e}")
            else:
                log(f"  Target not found: {target_file}")

    # Also replace default.metallib in Resources if it exists
    # This is crucial because libmlx.dylib might look for it there
    resources_dir = os.path.join(contents_dir, "Resources")
    default_metallib = os.path.join(resources_dir, "default.metallib")
    src_metallib = os.path.join(src_mlx_dir, "lib", "mlx.metallib")
    
    if os.path.exists(default_metallib) and os.path.exists(src_metallib):
        log(f"Found default.metallib in Resources, replacing with version from {src_metallib}")
        try:
            os.remove(default_metallib)
            shutil.copy2(src_metallib, default_metallib)
            log("  Replaced default.metallib")
            replaced_count += 1
        except Exception as e:
            log(f"  ERROR replacing default.metallib: {e}")
    
    log(f"Replacement complete. {replaced_count} files replaced.")

# Execute on import (before main app starts)
setup_mlx_libraries()
