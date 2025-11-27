# MLX Whisper Transcription Tool

This tool uses `mlx-whisper` (Whisper V3) to transcribe audio files on macOS using Apple Silicon GPU.

## Distribution Note

This application depends on `ffmpeg` being installed on the user's system. Due to this dependency and licensing complexities, **this application cannot be distributed via the Mac App Store**. It is intended for local use or distribution via direct download (e.g., DMG, Zip).

## Prerequisites

1.  **macOS with Apple Silicon** (M1/M2/M3/M4).
2.  **Python 3.8+**.
3.  **uv**: Fast Python package installer and resolver.
    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```
4.  **FFmpeg**: Required for audio processing.
    ```bash
    brew install ffmpeg
    ```

## Installation

1.  Clone this repository or navigate to the folder.
2.  Create a virtual environment and install dependencies using `uv`:
    ```bash
    # Create a virtual environment
    uv venv

    # Activate the virtual environment
    source .venv/bin/activate

    # Install packages
    uv pip install -r requirements.txt
    ```

## Usage

### GUI Application (Recommended)

Run the GUI application:

```bash
python gui.py
```

1.  Click **"Browse"** to select an audio file.
2.  Click **"Start Transcription"**.
3.  Wait for the process to complete. The status will be shown in the log area.
4.  The transcription will be saved as a `.txt` file in the same folder as the audio file.

### CLI Tool

Run the script with the path to your audio file:

```bash
python transcribe.py path/to/your/audio_file.mp3
```

## Model

This tool uses `mlx-community/whisper-large-v3` by default. The model will be downloaded automatically on the first run.
