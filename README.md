# TTS-v3: CSM-Powered Text-to-Speech

TTS-v3 is a web application that uses the Conversational Speech Model (CSM) to generate high-quality speech from text. This application combines a Flask backend with a responsive web frontend to provide an intuitive text-to-speech experience.

## Features

- High-quality speech synthesis using CSM
- Multiple speaker identities
- Adjustable playback speed and volume
- Word highlighting during playback
- GPU acceleration with memory optimization for 8GB GPUs
- Dark/light mode toggle
- Responsive design for desktop and mobile

## Requirements

- Python 3.10 or newer
- CUDA-compatible GPU (recommended for faster generation)
- Access to the Hugging Face models:
  - [Llama-3.2-1B](https://huggingface.co/meta-llama/Llama-3.2-1B)
  - [CSM-1B](https://huggingface.co/sesame/csm-1b)

## Installation

### Local Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd <repository-directory>
   ```

2. Install the required dependencies:
   ```bash
   pip install -r TTS-v3/requirements.txt
   ```

3. Log in to Hugging Face to access the required models:
   ```bash
   huggingface-cli login
   ```

4. Disable lazy compilation in Mimi:
   ```bash
   export NO_TORCH_COMPILE=1
   ```

### Docker Installation

TTS-v3 can also be run using Docker with GPU support:

1. Ensure you have Docker, docker-compose, and NVIDIA Container Toolkit installed:
   ```bash
   # Install NVIDIA Container Toolkit
   distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
   curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
   curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
   sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
   sudo systemctl restart docker
   ```

2. Build and run the Docker container:
   ```bash
   cd TTS-v3
   ./docker-run.sh --build
   ```

3. Access the application at http://localhost:5000

Docker script options:
```
./docker-run.sh [options]
Options:
  --build    Build the Docker image before starting
  --detach   Run in detached mode
  --logs     Follow the logs after starting
  --stop     Stop the running container
  --restart  Restart the container
  --help     Show this help message
```

### GitHub Actions CI/CD

TTS-v3 includes a GitHub Actions workflow for automated Docker builds:

- Automatically builds and pushes Docker images to GitHub Container Registry (ghcr.io)
- Includes NVIDIA GPU support in the container
- Creates versioned tags based on git tags and branches
- Generates a production-ready docker-compose.yml file as an artifact

To use the GitHub Container Registry image:

1. Pull the image:
   ```bash
   docker pull ghcr.io/your-username/your-repo-tts-v3:latest
   ```

2. Download the docker-compose.prod.yml file from the GitHub Actions artifacts

3. Run the container:
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

## Usage

### Running Locally

1. Start the server:
   ```bash
   cd TTS-v3
   python server.py
   ```

2. Open a web browser and navigate to:
   ```
   http://localhost:5000
   ```

3. Enter the text you want to convert to speech, select a speaker, and click the play button.

### Running with Docker

1. Start the container:
   ```bash
   cd TTS-v3
   ./docker-run.sh
   ```

2. Access the web interface at:
   ```
   http://localhost:5000
   ```

3. To stop the container:
   ```bash
   ./docker-run.sh --stop
   ```

## Memory Optimization for 8GB GPUs

TTS-v3 now uses GPU by default with memory optimization features for systems with limited GPU memory:

1. **Memory Settings Panel**: Access by clicking the ⚙️ icon in the controls section.
   - Switch between GPU and CPU processing
   - Enable/disable memory optimization

2. **GPU Optimizations**: 
   - Half-precision (FP16) for model parameters
   - Memory fraction limiting to prevent OOM errors
   - Aggressive memory cleanup between requests

3. **Automatic Fallback**: If an out-of-memory error occurs, the system will automatically switch to CPU mode.

4. **Command Line Testing**: Test memory usage with the test script:
   ```bash
   # Test with memory optimization (half precision is enabled by default)
   python test_csm.py
   
   # Test with full precision (uses more memory)
   python test_csm.py --no-half
   
   # Force CPU usage
   python test_csm.py --cpu
   
   # Specify custom text
   python test_csm.py --text "Your text here"
   ```

5. **Server Launch Options**:
   ```bash
   ./run_server.sh --cpu  # Force CPU mode if GPU has issues
   ```
   
   With Docker:
   ```bash
   # Edit docker-compose.yml to change DEFAULT_DEVICE to cpu
   # Then restart the container
   ./docker-run.sh --restart
   ```

## How It Works

TTS-v3 uses the Conversational Speech Model (CSM) developed by Sesame to generate speech. Unlike traditional TTS systems, CSM is designed to maintain speaker identity and conversational context, resulting in more natural-sounding speech.

The application consists of:

1. **Backend (server.py)**: A Flask server that handles API requests, loads the CSM model, and generates speech.
2. **Frontend (HTML/CSS/JS)**: A responsive web interface that allows users to input text, select speakers, and control playback.

## Notes

- First-time speech generation may take longer as the model loads into GPU memory
- CSM works best with conversational text and can maintain speaker identity across multiple generations.
- The application includes watermarking in the generated audio to identify it as AI-generated content.
- For systems with 8GB GPUs, GPU acceleration with memory optimization is enabled by default
- If you experience "Out of Memory" errors:
  1. Try enabling memory optimization in the settings panel
  2. Switch to CPU mode if problems persist
  3. Reduce the length of text being synthesized

## Differences from TTS-v2

TTS-v3 is based on TTS-v2 but replaces the MeloTTS library with the CSM model. Key differences include:

- **Speech Quality**: CSM provides more natural, conversational speech compared to MeloTTS.
- **Speaker Options**: Instead of language-specific voices, TTS-v3 uses different speaker IDs.
- **Generation Time**: CSM may take longer to generate speech but produces higher quality results.
- **Context Awareness**: CSM is designed to maintain speaker identity across multiple generations.
- **Memory Management**: TTS-v3 includes memory optimization for systems with limited GPU memory.

## License

This project uses components with various licenses:
- CSM is released under the Apache 2.0 license
- The web interface is MIT licensed