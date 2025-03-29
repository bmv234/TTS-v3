#!/bin/bash

# Default settings
export NO_TORCH_COMPILE=1
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
export DEFAULT_DEVICE=cuda
USE_CPU=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --cpu)
            USE_CPU=true
            shift
            ;;
        --help)
            echo "Usage: ./run_server.sh [options]"
            echo ""
            echo "Options:"
            echo "  --cpu       Force CPU usage even if CUDA is available"
            echo "  --help      Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Check if Python is available
if command -v python3 &>/dev/null; then
    PYTHON_CMD=python3
elif command -v python &>/dev/null; then
    PYTHON_CMD=python
else
    echo "Error: Python not found. Please install Python 3.10 or newer."
    exit 1
fi

# Check if the user is logged in to Hugging Face
echo "Checking Hugging Face login status..."
if ! $PYTHON_CMD -c "from huggingface_hub import HfApi; api = HfApi(); print(api.whoami())" &>/dev/null; then
    echo "Warning: You may not be logged in to Hugging Face."
    echo "This is required to access the CSM and Llama models."
    echo "Please run 'huggingface-cli login' before starting the server."
    
    read -p "Do you want to continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Set default device based on arguments
if [ "$USE_CPU" = true ]; then
    echo "Forcing CPU mode as requested"
    export DEFAULT_DEVICE=cpu
fi

# Start the server
echo "Starting CSM TTS server..."
echo "The server will be available at http://localhost:5000"
echo "Using device: ${DEFAULT_DEVICE}"
echo "Memory optimization: ENABLED (recommended for 8GB GPUs)"
echo "Press Ctrl+C to stop the server"
echo

# Change to the script's directory
cd "$(dirname "$0")"

# Run the server
$PYTHON_CMD server.py