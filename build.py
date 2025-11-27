import PyInstaller.__main__
import os
import shutil
import customtkinter
import subprocess

# Get customtkinter path to include its data files
ctk_path = os.path.dirname(customtkinter.__file__)

app_name = "MLXWhisperTranscriber"

print("Building Application Bundle...")
PyInstaller.__main__.run([
    'gui.py',
    '--name=MLXWhisperTranscriber',
    '--windowed',  # No terminal window
    '--icon=app_icon.icns', # Application Icon
    '--onedir',    # Create a directory (easier for debugging than --onefile)
    '--clean',
    '--noconfirm',
    '--hidden-import=mlx',
    '--hidden-import=mlx.core',
    '--hidden-import=mlx.nn',
    '--collect-all=mlx',
    '--collect-all=mlx_whisper',
    f'--add-data={ctk_path}:customtkinter',  # Include customtkinter themes/images
])

print("Creating DMG Installer...")

dist_dir = "dist"
app_path = os.path.join(dist_dir, f"{app_name}.app")
dmg_path = os.path.join(dist_dir, f"{app_name}.dmg")
tmp_dmg_dir = os.path.join(dist_dir, "dmg_temp")

# Clean up previous DMG and temp dir
if os.path.exists(dmg_path):
    os.remove(dmg_path)
if os.path.exists(tmp_dmg_dir):
    shutil.rmtree(tmp_dmg_dir)

# Create temp dir for DMG content
os.makedirs(tmp_dmg_dir)

# Copy App to temp dir
print(f"Copying {app_name}.app to temporary DMG folder...")
shutil.copytree(app_path, os.path.join(tmp_dmg_dir, f"{app_name}.app"))

# Create symlink to /Applications
print("Creating /Applications link...")
os.symlink("/Applications", os.path.join(tmp_dmg_dir, "Applications"))

# Create DMG
print(f"Generating {app_name}.dmg...")
subprocess.run([
    "hdiutil", "create",
    "-volname", app_name,
    "-srcfolder", tmp_dmg_dir,
    "-ov",
    "-format", "UDZO",
    dmg_path
], check=True)

# Cleanup
shutil.rmtree(tmp_dmg_dir)

print(f"Build Complete! DMG is available at: {dmg_path}")
