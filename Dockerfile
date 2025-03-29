FROM nvidia/cuda:12.4.0-runtime-ubuntu22.04

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive \
    NO_TORCH_COMPILE=1 \
    PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 \
    python3-pip \
    python3-dev \
    python3-setuptools \
    python3-wheel \
    git \
    ffmpeg \
    libsndfile1 \
    wget \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Install Hugging Face CLI
RUN pip3 install --no-cache-dir huggingface_hub[cli]

# Copy application code
COPY . .

# Create a directory for CSM
RUN mkdir -p /app/csm

# Clone the CSM repository directly into the container
RUN apt-get update && apt-get install -y git && \
    git clone https://github.com/SesameAILabs/csm.git /app/csm && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Set up Hugging Face cache directory
ENV HF_HOME=/app/.cache/huggingface

# Expose port
EXPOSE 5000

# Set entrypoint
ENTRYPOINT ["python3", "server.py"]