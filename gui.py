import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import os
import mlx_whisper
import shutil
import truststore
import webbrowser
import subprocess
import multiprocessing
import sys
import queue
import json
from huggingface_hub import try_to_load_from_cache

# Inject system trust store for corporate proxies/SSL inspection
truststore.inject_into_ssl()

# Add Homebrew paths to PATH for macOS app bundles (GUI apps don't inherit shell PATH)
os.environ["PATH"] += os.pathsep + "/opt/homebrew/bin" + os.pathsep + "/usr/local/bin"

CONFIG_FILE = os.path.expanduser("~/.mlx_whisper_config.json")

# Configuration
ctk.set_appearance_mode("System")  # Modes: "System" (standard), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

def transcription_worker(result_queue, audio_path, model_name, language_code, language_name):
    """
    Worker process for transcription.
    Runs in a separate process to allow termination (Stop button).
    """
    import sys
    import os
    import time
    # Re-import necessary modules in the new process
    import mlx_whisper
    import truststore
    
    # Re-inject truststore and path
    truststore.inject_into_ssl()
    # Ensure PATH is correct in the subprocess
    if "/opt/homebrew/bin" not in os.environ["PATH"]:
        os.environ["PATH"] += os.pathsep + "/opt/homebrew/bin" + os.pathsep + "/usr/local/bin"

    class QueueLogger:
        def __init__(self, queue):
            self.queue = queue
        def write(self, msg):
            # Filter out empty newlines to reduce queue traffic
            if msg:
                self.queue.put(("log", msg))
        def flush(self):
            pass

    # Redirect stdout/stderr to the queue
    sys.stdout = QueueLogger(result_queue)
    sys.stderr = QueueLogger(result_queue)

    try:
        print(f"Starting transcription for: {audio_path}")
        print(f"Loading model ({model_name})...")

        transcribe_args = {
            "audio": audio_path,
            "path_or_hf_repo": model_name,
            "verbose": True
        }
        
        if language_code:
            transcribe_args["language"] = language_code
            print(f"Language set to: {language_name} ({language_code})")
        else:
            print("Language: Auto-detect")

        # Run transcription
        start_time = time.time()
        result = mlx_whisper.transcribe(**transcribe_args)
        end_time = time.time()
        duration = end_time - start_time
        
        # Send result back
        result_queue.put(("success", (result["text"], duration)))
        
    except Exception as e:
        result_queue.put(("error", str(e)))


class App(ctk.CTk):
    MODEL_INFO = {
        "mlx-community/whisper-tiny": "Speed: ★★★★★ | Accuracy: ★☆☆☆☆ (Fastest, MLX Optimized)",
        "mlx-community/whisper-base": "Speed: ★★★★☆ | Accuracy: ★★☆☆☆ (Fast, MLX Optimized)",
        "mlx-community/whisper-small": "Speed: ★★★☆☆ | Accuracy: ★★★☆☆ (Balanced, MLX Optimized)",
        "mlx-community/whisper-medium": "Speed: ★★☆☆☆ | Accuracy: ★★★★☆ (High Accuracy, MLX Optimized)",
        "mlx-community/whisper-large-v3": "Speed: ★☆☆☆☆ | Accuracy: ★★★★★ (Best Accuracy, MLX Optimized)",
        "mlx-community/whisper-large-v3-mlx": "Speed: ★☆☆☆☆ | Accuracy: ★★★★★ (Best Accuracy, MLX Optimized)",
        "mlx-community/whisper-large-v3-turbo": "Speed: ★★★☆☆ | Accuracy: ★★★★★ (Fast, High Accuracy, Recommended, MLX Optimized)",
    }

    LANGUAGE_CODES = {
        "English": "en",
        "Japanese": "ja",
        "Chinese": "zh",
        "Korean": "ko",
        "Spanish": "es",
        "French": "fr",
        "German": "de",
        "Italian": "it",
        "Russian": "ru",
        "Portuguese": "pt"
    }

    def __init__(self):
        super().__init__()

        # Window setup
        self.title("MLX Whisper Transcriber")
        self.geometry("850x550")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # Check for FFmpeg
        if not shutil.which("ffmpeg"):
            messagebox.showwarning("Missing Dependency", "FFmpeg not found.\nPlease install it via 'brew install ffmpeg' to ensure audio processing works.")

        # Title Label
        self.title_label = ctk.CTkLabel(self, text="MLX Whisper Transcriber", font=ctk.CTkFont(size=20, weight="bold"))
        self.title_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        # File Selection Frame
        self.file_frame = ctk.CTkFrame(self)
        self.file_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        self.file_frame.grid_columnconfigure(0, weight=1)

        self.file_path_entry = ctk.CTkEntry(self.file_frame, placeholder_text="Select an audio file...")
        self.file_path_entry.grid(row=0, column=0, padx=(10, 10), pady=10, sticky="ew")

        self.browse_button = ctk.CTkButton(self.file_frame, text="Browse", command=self.browse_file, width=100)
        self.browse_button.grid(row=0, column=1, padx=(0, 10), pady=10)

        # Model Selection
        self.model_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.model_frame.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="ew")
        self.model_frame.grid_columnconfigure(1, weight=1)

        # Row 0: Controls
        self.model_label = ctk.CTkLabel(self.model_frame, text="Model:", font=ctk.CTkFont(weight="bold"))
        self.model_label.grid(row=0, column=0, padx=(0, 10), sticky="w")

        self.model_var = ctk.StringVar(value="mlx-community/whisper-large-v3")
        self.model_select_menu = ctk.CTkOptionMenu(
            self.model_frame,
            values=[
                "mlx-community/whisper-large-v3",
                "mlx-community/whisper-large-v3-mlx",
                "mlx-community/whisper-large-v3-turbo",
                "mlx-community/whisper-tiny",
                "mlx-community/whisper-base",
                "mlx-community/whisper-small",
                "mlx-community/whisper-medium"
            ],
            variable=self.model_var,
            command=self.on_model_change
        )
        self.model_select_menu.grid(row=0, column=1, padx=(0, 10), sticky="ew")

        self.local_model_button = ctk.CTkButton(self.model_frame, text="Load Local...", command=self.select_local_model, width=100, fg_color="green")
        self.local_model_button.grid(row=0, column=2, padx=(0, 10), sticky="w")

        self.help_button = ctk.CTkButton(self.model_frame, text="?", command=self.show_help, width=30, fg_color="gray")
        self.help_button.grid(row=0, column=3, padx=(0, 10), sticky="w")

        self.cache_status_label = ctk.CTkLabel(self.model_frame, text="Checking...", text_color="gray")
        self.cache_status_label.grid(row=0, column=4, padx=(0, 0), sticky="w")

        # Row 1: Path/URL Display
        self.path_label = ctk.CTkLabel(self.model_frame, text="Source:", font=ctk.CTkFont(size=12))
        self.path_label.grid(row=1, column=0, padx=(0, 10), pady=(5, 0), sticky="w")

        self.model_source_link = ctk.CTkButton(
            self.model_frame,
            text="mlx-community/whisper-large-v3",
            fg_color="transparent",
            text_color=("blue", "#4DA6FF"),
            anchor="w",
            font=ctk.CTkFont(size=12, underline=True),
            hover_color=("gray85", "gray25"),
            command=self.open_source
        )
        self.model_source_link.grid(row=1, column=1, columnspan=4, padx=(0, 0), pady=(5, 0), sticky="ew")

        # Row 2: Model Info
        self.model_info_label = ctk.CTkLabel(self.model_frame, text="", text_color="gray", font=ctk.CTkFont(size=12))
        self.model_info_label.grid(row=2, column=0, columnspan=5, padx=(0, 10), pady=(5, 0), sticky="w")

        # Variables
        self.selected_file = None
        self.is_transcribing = False
        self.process = None
        self.result_queue = None
        # Remember last visited directory for models
        self.last_model_dir = os.path.join(os.getcwd(), "models") if os.path.exists(os.path.join(os.getcwd(), "models")) else os.getcwd()

        # Initial check
        self.on_model_change(self.model_var.get())

        # Options Frame (Language)
        self.options_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.options_frame.grid(row=3, column=0, padx=20, pady=(0, 10), sticky="ew")

        self.language_label = ctk.CTkLabel(self.options_frame, text="Language:", font=ctk.CTkFont(weight="bold"))
        self.language_label.grid(row=0, column=0, padx=(0, 10), sticky="w")

        self.language_var = ctk.StringVar(value="Auto")
        self.language_menu = ctk.CTkOptionMenu(
            self.options_frame,
            values=["Auto"] + list(self.LANGUAGE_CODES.keys()),
            variable=self.language_var
        )
        self.language_menu.grid(row=0, column=1, padx=(0, 10), sticky="w")

        # Status / Result Area (Tabs)
        self.tabview = ctk.CTkTabview(self, width=500, height=200)
        self.tabview.grid(row=4, column=0, padx=20, pady=10, sticky="nsew")
        self.grid_rowconfigure(4, weight=1) # Make the text area expandable
        
        self.tab_logs = self.tabview.add("Logs")
        self.tab_result = self.tabview.add("Result")
        
        # Log Textbox
        self.tabview.set("Logs")
        self.log_textbox = ctk.CTkTextbox(self.tab_logs, width=500, height=150)
        self.log_textbox.pack(expand=True, fill="both")
        self.log_textbox.insert("0.0", "Ready to transcribe.\n")
        self.log_textbox.configure(state="disabled")

        # Result Textbox
        self.result_textbox = ctk.CTkTextbox(self.tab_result, width=500, height=150)
        self.result_textbox.pack(expand=True, fill="both")

        # Action Buttons
        self.button_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.button_frame.grid(row=5, column=0, padx=20, pady=20)

        self.transcribe_button = ctk.CTkButton(self.button_frame, text="Start Transcription", command=self.start_transcription_thread, font=ctk.CTkFont(size=15, weight="bold"), height=40, width=200)
        self.transcribe_button.pack()

        # Progress Bar (Indeterminate)
        self.progress_bar = ctk.CTkProgressBar(self.button_frame, width=400, mode="indeterminate")
        # self.progress_bar.pack(pady=10) # Packed only when running
        
        # Load saved configuration
        self.load_config()

    def load_config(self):
        """Load configuration from JSON file."""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    config = json.load(f)
                    
                # Restore last model directory
                if "last_model_dir" in config and os.path.isdir(config["last_model_dir"]):
                    self.last_model_dir = config["last_model_dir"]
                
                # Restore last selected model
                if "last_model" in config:
                    last_model = config["last_model"]
                    # If it's a local path, ensure it exists and add to dropdown
                    if os.path.isdir(last_model):
                        if last_model not in self.model_select_menu._values:
                            current_values = self.model_select_menu._values
                            self.model_select_menu.configure(values=[last_model] + current_values)
                        self.model_var.set(last_model)
                        self.on_model_change(last_model)
                    # If it's a HF repo, just set it
                    elif last_model in self.model_select_menu._values:
                        self.model_var.set(last_model)
                        self.on_model_change(last_model)
                        
            except Exception as e:
                print(f"Failed to load config: {e}")

    def save_config(self):
        """Save configuration to JSON file."""
        config = {
            "last_model_dir": self.last_model_dir,
            "last_model": self.model_var.get()
        }
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(config, f)
        except Exception as e:
            print(f"Failed to save config: {e}")

    def select_local_model(self):
        folder_path = filedialog.askdirectory(title="Select Model Folder", initialdir=self.last_model_dir)
        if not folder_path:
            return
        
        # Update last visited directory (parent of the selected folder)
        self.last_model_dir = os.path.dirname(folder_path)
        self.save_config()

        # Check if config.json exists, if not search subdirectories
        found_paths = []
        
        # Check root first
        if os.path.exists(os.path.join(folder_path, "config.json")):
            found_paths.append(folder_path)
        else:
            self.log_message("Searching for models in subdirectories...")
            for root, dirs, files in os.walk(folder_path):
                if "config.json" in files:
                    found_paths.append(root)
                    # Don't traverse inside a model folder (optimization)
                    dirs[:] = []
        
        if not found_paths:
            messagebox.showwarning("Invalid Model Folder", "Could not find 'config.json' in the selected folder or its subdirectories.\nPlease select a valid Hugging Face model folder.")
            return

        # Sort paths to ensure consistent order
        found_paths.sort()

        # Update dropdown with found local models
        current_values = self.model_select_menu._values
        # Add new paths to the top, removing duplicates
        new_values = found_paths + [v for v in current_values if v not in found_paths]
        self.model_select_menu.configure(values=new_values)

        # Select the first found model (or the one that matches current selection if possible?)
        # For now, just select the first one found, but let user switch.
        target_path = found_paths[0]
        self.model_var.set(target_path)
        self.on_model_change(target_path)
        
        self.log_message(f"Selected local model path: {target_path}")
        if len(found_paths) > 1:
            self.log_message(f"Found {len(found_paths)} models in the folder. You can switch between them in the dropdown.")
        elif target_path != folder_path:
            self.log_message(f"(Auto-detected model inside subfolder)")

    def show_help(self):
        help_text = (
            "How to use Local Models (Offline Mode):\n\n"
            "1. Go to Hugging Face (e.g., https://huggingface.co/mlx-community/whisper-large-v3/tree/main).\n"
            "2. Download all files (or clone the repo) into a folder.\n"
            "   Required files: config.json, model.safetensors (or weights.npz), tokenizer.json, etc.\n"
            "3. Click 'Load Local...' and select that folder.\n\n"
            "This allows you to use the app even if the corporate firewall blocks automatic downloads."
        )
        messagebox.showinfo("Help: Manual Download", help_text)

    def on_model_change(self, model_name):
        # Save the new selection
        self.save_config()

        # Update URL/Path display
        if os.path.isdir(model_name):
            self.current_source = model_name
            self.model_source_link.configure(text=model_name)
            self.cache_status_label.configure(text="Local Folder", text_color="blue")
            self.model_info_label.configure(text="Local Model (Details unknown)")
        else:
            url = f"https://huggingface.co/{model_name}"
            self.current_source = url
            self.model_source_link.configure(text=url)
            
            # Update Info
            info_text = self.MODEL_INFO.get(model_name, "No information available")
            self.model_info_label.configure(text=info_text)
            
            # Check cache status
            cached_path = try_to_load_from_cache(repo_id=model_name, filename="config.json")
            if cached_path:
                self.cache_status_label.configure(text="✓ Cached", text_color="green")
            else:
                self.cache_status_label.configure(text="⚠ Not Cached", text_color="orange")

    def open_source(self):
        if hasattr(self, 'current_source') and self.current_source:
            if os.path.isdir(self.current_source):
                subprocess.run(["open", self.current_source])
            else:
                webbrowser.open(self.current_source)

    def browse_file(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Audio Files", "*.mp3 *.wav *.m4a *.mp4 *.flac"), ("All Files", "*.*")]
        )
        if file_path:
            self.selected_file = file_path
            self.file_path_entry.delete(0, "end")
            self.file_path_entry.insert(0, file_path)
            self.log_message(f"Selected file: {os.path.basename(file_path)}")

    def log_message(self, message):
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", message + "\n")
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")

    def start_transcription_thread(self):
        if not self.selected_file:
            messagebox.showwarning("No File", "Please select an audio file first.")
            return
        
        if self.is_transcribing:
            return

        self.is_transcribing = True
        self.transcribe_button.configure(text="Stop Transcription", fg_color="red", hover_color="darkred", command=self.stop_transcription)
        self.browse_button.configure(state="disabled")
        
        # Show and start progress bar
        self.progress_bar.pack(pady=10)
        self.progress_bar.start()

        # Prepare arguments
        audio_path = self.selected_file
        model_name = self.model_var.get()
        language_selection = self.language_var.get()
        language_code = None
        if language_selection != "Auto":
            language_code = self.LANGUAGE_CODES.get(language_selection)

        # Create Queue
        self.result_queue = multiprocessing.Queue()

        # Start Process
        self.process = multiprocessing.Process(
            target=transcription_worker,
            args=(self.result_queue, audio_path, model_name, language_code, language_selection)
        )
        self.process.start()

        # Start polling the queue
        self.after(100, self.check_queue)

    def stop_transcription(self):
        if self.process and self.process.is_alive():
            self.process.terminate()
            self.log_message("\n[Stopped] Transcription stopped by user.")
            self.reset_ui()

    def check_queue(self):
        try:
            while True:
                # Get all available messages
                msg_type, content = self.result_queue.get_nowait()
                
                if msg_type == "log":
                    self.log_message_no_newline(content)
                elif msg_type == "success":
                    self.handle_success(content)
                    return
                elif msg_type == "error":
                    self.handle_error(content)
                    return
        except queue.Empty:
            pass
        
        if self.process and self.process.is_alive():
            self.after(100, self.check_queue)
        else:
            # Process died unexpectedly or finished without sending success/error
            if self.is_transcribing:
                # self.reset_ui() # Don't reset immediately, might be just empty queue for a moment
                self.after(100, self.check_queue)

    def handle_success(self, content):
        text, duration = content
        
        # Format duration
        minutes, seconds = divmod(duration, 60)
        if minutes > 0:
            time_str = f"{int(minutes)}m {int(seconds)}s"
        else:
            time_str = f"{duration:.1f}s"

        # Save to file
        base_name = os.path.splitext(self.selected_file)[0]
        output_path = f"{base_name}.txt"
        
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(text)
            self.log_message(f"SUCCESS: Transcription saved to:\n{output_path}")
            self.log_message(f"Time taken: {time_str}")
            self.show_transcription_result(text)
            messagebox.showinfo("Success", f"Transcription completed successfully!\nTime taken: {time_str}")
        except Exception as e:
            self.log_message(f"Error saving file: {e}")
            messagebox.showerror("Error", f"Could not save file: {e}")
        
        self.reset_ui()

    def handle_error(self, error_msg):
        if "Expecting value" in error_msg or "JSONDecodeError" in error_msg:
            model_url = f"https://huggingface.co/{self.model_var.get()}"
            error_msg += f"\n\nPossible Cause: Corporate Firewall (Cisco Umbrella) is blocking Hugging Face.\n\nSOLUTION:\n1. Open this URL in your browser:\n{model_url}\n2. Click 'Continue' on the warning page.\n3. Try again."
        
        self.log_message(f"ERROR: {error_msg}")
        messagebox.showerror("Error", f"An error occurred:\n{error_msg}")
        self.reset_ui()

    def log_message_no_newline(self, message):
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", message)
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")

    def run_transcription(self):
        # Deprecated, replaced by transcription_worker
        pass

    def show_transcription_result(self, text):
        self.result_textbox.delete("0.0", "end")
        self.result_textbox.insert("0.0", text)
        self.tabview.set("Result")

    def reset_ui(self):
        self.is_transcribing = False
        self.transcribe_button.configure(text="Start Transcription", fg_color=["#3B8ED0", "#1F6AA5"], hover_color=["#36719F", "#144870"], command=self.start_transcription_thread)
        self.browse_button.configure(state="normal")
        self.progress_bar.stop()
        self.progress_bar.pack_forget()

if __name__ == "__main__":
    multiprocessing.freeze_support()
    app = App()
    app.mainloop()
