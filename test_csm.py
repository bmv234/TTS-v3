import os
import sys
import torch
import torchaudio
import gc
import argparse

# Add the CSM directory to the path
sys.path.append('../csm')

# Disable Triton compilation
os.environ["NO_TORCH_COMPILE"] = "1"

# Set PyTorch memory management options
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

# Set memory fraction to avoid OOM
if torch.cuda.is_available():
    torch.cuda.set_per_process_memory_fraction(0.8)

# Import CSM modules
from generator import Segment
from csm_generator import load_csm_generator

def test_csm(use_cpu=False, use_half_precision=True, text=None):
    try:
        print("Testing CSM text-to-speech generation...")
        
        # Select the best available device
        if torch.cuda.is_available() and not use_cpu:
            device = "cuda"
            print("Using CUDA for inference")
            
            # Print GPU memory information
            free_memory = torch.cuda.get_device_properties(0).total_memory - torch.cuda.memory_allocated(0)
            free_memory_gb = free_memory / (1024**3)
            total_memory_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            print(f"GPU Memory: {free_memory_gb:.2f}GB free / {total_memory_gb:.2f}GB total")
            
            # Clean up memory before loading model
            torch.cuda.empty_cache()
            gc.collect()
        else:
            device = "cpu"
            print("Using CPU for inference (this will be slow)")
        
        if use_half_precision and device == "cuda":
            print("Using half precision (FP16) to reduce memory usage")
        
        # Load the CSM model
        print("Loading CSM model (this may take a moment)...")
        generator = load_csm_generator(device=device, use_half_precision=use_half_precision)
        print(f"Model loaded successfully. Sample rate: {generator.sample_rate}Hz")
        
        # Generate speech
        if text is None:
            text = "Hello, this is a test of the CSM text-to-speech system."
        speaker_id = 0
        
        print(f"Generating speech for text: '{text}' with speaker ID: {speaker_id}")
        audio = generator.generate(
            text=text,
            speaker=speaker_id,
            context=[],  # Empty context
            max_audio_length_ms=10_000,  # 10 seconds max
        )
        
        # Save the audio to a file
        output_path = "test_output.wav"
        torchaudio.save(
            output_path,
            audio.unsqueeze(0).cpu(),
            generator.sample_rate
        )
        
        print(f"Test successful - audio file generated as {output_path}")
        print(f"Audio duration: {audio.shape[0] / generator.sample_rate:.2f} seconds")
        
        return True
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Test CSM text-to-speech generation')
    parser.add_argument('--cpu', action='store_true', help='Force CPU usage even if CUDA is available')
    parser.add_argument('--no-half', action='store_true', help='Disable half precision (use full precision)')
    parser.add_argument('--text', type=str, help='Text to synthesize')
    args = parser.parse_args()
    
    test_csm(use_cpu=args.cpu, use_half_precision=not args.no_half, text=args.text)