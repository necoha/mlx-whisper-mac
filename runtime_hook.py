"""
Runtime hook for PyInstaller.
This runs BEFORE the main application and any imports.
Detects macOS version and replaces mlx package if needed.
"""
import os
import sys
import platform
import shutil
import zipfile
import tempfile

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
    
    log("macOS < 26, need to use compatible mlx package")
    
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
    
    # Look for macos15_mlx.zip in Resources
    zip_path = os.path.join(contents_dir, "Resources", "macos15_mlx.zip")
    
    if not os.path.exists(zip_path):
        log(f"ERROR: macos15_mlx.zip not found at {zip_path}")
        # Fallback check in bundle_dir
        zip_path = os.path.join(bundle_dir, "macos15_mlx.zip")
        if not os.path.exists(zip_path):
             log(f"ERROR: macos15_mlx.zip not found at {zip_path} either")
             return

    log(f"Found zip: {zip_path}")
    
    # Extract to a temporary directory
    # We use a fixed name based on version to avoid re-extracting if possible, 
    # but /tmp is usually cleaned up.
    extract_root = os.path.join(tempfile.gettempdir(), "mlx_whisper_macos15_v1.0.13")
    
    # Check if already extracted and valid? 
    # For safety, we can just overwrite or check if dir exists.
    # Since /tmp is per-user usually, this is fine.
    
    if not os.path.exists(extract_root):
        log(f"Extracting to {extract_root}...")
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_root)
            log("Extraction complete")
        except Exception as e:
            log(f"Extraction failed: {e}")
            return
    else:
        log(f"Using existing extraction at {extract_root}")

    # The zip structure is macos15_mlx/mlx/...
    # We want to add the directory containing 'mlx' package to sys.path.
    # That directory is extract_root/macos15_mlx
    
    site_packages = os.path.join(extract_root, "macos15_mlx")
    if not os.path.exists(os.path.join(site_packages, "mlx")):
        log(f"ERROR: mlx package not found in {site_packages}")
        return
        
    # Prepend to sys.path to take precedence over bundled mlx
    sys.path.insert(0, site_packages)
    log(f"Added {site_packages} to sys.path")
    log(f"sys.path[0]: {sys.path[0]}")

# Execute on import (before main app starts)
setup_mlx_libraries()
