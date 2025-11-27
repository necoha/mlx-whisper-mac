import PyInstaller.__main__
import os
import shutil
import customtkinter

# Get customtkinter path to include its data files
ctk_path = os.path.dirname(customtkinter.__file__)

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
