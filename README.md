# MLX Whisper Transcriber for macOS

A standalone macOS GUI application for OpenAI's Whisper model, optimized for Apple Silicon using [MLX](https://github.com/ml-explore/mlx).

![App Icon](icon_master.png)

## Features

*   **Apple Silicon Optimized**: Runs locally on your Mac's GPU/NPU using MLX.
*   **Offline Capable**: Supports loading models from local folders (great for corporate environments).
*   **User Friendly**: Simple GUI with drag-and-drop support (via file browse).
*   **Language Support**: Auto-detection or manual selection (English, Japanese, etc.).
*   **Progress Tracking**: Real-time logs and progress bar.

## Prerequisites

*   **macOS with Apple Silicon** (M1/M2/M3/M4).
*   **FFmpeg**: Required for audio processing.
    ```bash
    brew install ffmpeg
    ```

## Installation & Usage

### Option 1: Run from Source (Developers)

1.  **Install uv** (Fast Python package manager):
    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```

2.  **Clone and Setup**:
    ```bash
    git clone https://github.com/necoha/mlx-whisper-mac.git
    cd mlx-whisper-mac
    
    # Create virtual environment and install dependencies
    uv venv
    source .venv/bin/activate
    uv pip install -r requirements.txt
    ```

3.  **Run the App**:
    ```bash
    python gui.py
    ```

### Option 2: Build Standalone App

You can package the application into a standard macOS `.app` bundle.

1.  Follow the "Run from Source" steps to set up your environment.
2.  Run the build script:
    ```bash
    python build.py
    ```
3.  The application will be created in the `dist/` folder:
    *   `dist/MLXWhisperTranscriber.app`

You can drag this app to your Applications folder. **Note:** You still need `ffmpeg` installed via Homebrew.

## Troubleshooting

*   **"FFmpeg not found"**: Make sure you installed it with `brew install ffmpeg`. The app looks in `/opt/homebrew/bin`.
*   **"App is damaged"**: If you move the app to another computer, you might need to remove the quarantine attribute:
    ```bash
    xattr -cr /Applications/MLXWhisperTranscriber.app
    ```

## License

MIT

