"""
Runtime hook for PyInstaller.
This runs BEFORE the main application and any imports.
Detects macOS version and modifies sys.path to load the correct mlx package.
"""
import os
import sys
import platform

def log(msg):
    """Write to stderr and a log file for debugging."""
    sys.stderr.write(f"[runtime_hook] {msg}\n")
    sys.stderr.flush()
    try:
        log_path = os.path.expanduser("~/Desktop/mlx_whisper_debug.log")
        with open(log_path, "a") as f:
            import datetime
            timestamp = datetime.datetime.now().isoformat()
            f.write(f"[{timestamp}] [PID:{os.getpid()}] {msg}\n")
    except:
        pass

def get_macos_version():
    """Get macOS major version number."""
    try:
        version = platform.mac_ver()[0]  # e.g., "15.7.2" or "26.1"
        if not version:
            return 15 # Fallback
        major = int(version.split('.')[0])
        return major
    except:
        return 15  # Default to macOS 15 if detection fails

def setup_mlx_path():
    """Prepend compatible mlx package path to sys.path."""
    if not getattr(sys, 'frozen', False):
        log("Not frozen, skipping")
        return
    
    macos_version = get_macos_version()
    log(f"macOS version: {macos_version}")
    
    # Only needed for macOS < 26 (assuming 26 is the cutoff for the new mlx)
    # Adjust this logic based on which version needs the "old" mlx
    if macos_version >= 26:
        log("macOS 26+, using default bundled libraries")
        return
    
    log("macOS < 26, switching to macos15_mlx package")
    
    # Determine paths
    if hasattr(sys, '_MEIPASS'):
        # Onefile (not used currently, but for completeness)
        bundle_dir = sys._MEIPASS
    else:
        # Onedir
        # sys.executable -> Contents/MacOS/MLXWhisperTranscriber
        app_dir = os.path.dirname(sys.executable)
        contents_dir = os.path.dirname(app_dir)
        # We put macos15_mlx in Contents/Resources/macos15_mlx
        
        resources_dir = os.path.join(contents_dir, "Resources")
        macos15_mlx_path = os.path.join(resources_dir, "macos15_mlx")
        
        if os.path.exists(macos15_mlx_path):
            log(f"Found macos15_mlx at: {macos15_mlx_path}")
            # Prepend to sys.path so it takes precedence over standard library
            sys.path.insert(0, macos15_mlx_path)
            log("Added to sys.path[0]")
            
            # Verify
            try:
                import importlib.util
                spec = importlib.util.find_spec("mlx")
                if spec:
                    log(f"mlx resolves to: {spec.origin}")
            except Exception as e:
                log(f"Could not verify mlx import: {e}")
        else:
            log(f"ERROR: macos15_mlx not found at {macos15_mlx_path}")

# Execute on import
setup_mlx_path()
