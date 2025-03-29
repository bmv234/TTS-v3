"""
Modified version of CSM generator.py for TTS-v3 with memory optimizations
"""
import os
import sys
import torch
import torchaudio
import gc
import logging

# Add the CSM directory to the path
sys.path.append('../csm')

# Configure logging
logger = logging.getLogger(__name__)

# Import original CSM modules
from generator import Segment

class CSMGenerator:
    """
    Memory-optimized wrapper for CSM generator
    """
    def __init__(self, device="cpu", use_half_precision=False):
        self.device = device
        self.use_half_precision = use_half_precision
        self._model = None
        self._text_tokenizer = None
        self._audio_tokenizer = None
        self._watermarker = None
        self.sample_rate = 24000  # Default sample rate
        
        # Initialize the generator
        self._initialize()
    
    def _initialize(self):
        """Initialize the CSM generator with memory optimizations"""
        try:
            logger.info(f"Initializing CSM generator on {self.device} with half precision: {self.use_half_precision}")
            
            # Import here to avoid circular imports
            from generator import load_csm_1b
            
            # Clean up memory before loading
            if self.device == "cuda":
                torch.cuda.empty_cache()
                # Set memory fraction to avoid OOM
                torch.cuda.set_per_process_memory_fraction(0.8)
            gc.collect()
            
            # Load model with optimizations
            if self.device == "cuda":
                logger.info("Loading model with CUDA optimizations")
                if self.use_half_precision:
                    # Load directly to GPU with half precision
                    logger.info("Using half precision (float16) to reduce memory usage")
                    with torch.cuda.amp.autocast():
                        model = load_csm_1b(device="cpu")  # Load to CPU first
                        
                        # Move model components to GPU with half precision
                        model._model.to(device=self.device, dtype=torch.float16)
                        
                        # Keep tokenizers on CPU to save memory
                        model._text_tokenizer = model._text_tokenizer
                        model._audio_tokenizer = model._audio_tokenizer
                        model._watermarker = model._watermarker
                else:
                    # Load with full precision
                    logger.info("Using full precision (float32)")
                    model = load_csm_1b(device=self.device)
            else:
                # Load on CPU
                logger.info("Loading model on CPU")
                model = load_csm_1b(device="cpu")
            
            self._model = model
            self._text_tokenizer = model._text_tokenizer
            self._audio_tokenizer = model._audio_tokenizer
            self._watermarker = model._watermarker
            self.sample_rate = model.sample_rate

            logger.info(f"CSM model loaded successfully on {self.device}")
            
        except Exception as e:
            logger.error(f"Error initializing CSM generator: {str(e)}")
            raise
    
    def generate(self, text, speaker, context=None, max_audio_length_ms=10000, temperature=0.9, topk=50):
        """Generate speech using CSM with memory optimizations"""
        if context is None:
            context = []
            
        try:
            # Clean up memory before generation
            if self.device == "cuda":
                torch.cuda.empty_cache()
                
            gc.collect()
            
            # Generate speech with half precision if enabled
            if self.device == "cuda" and self.use_half_precision:
                with torch.cuda.amp.autocast():
                    audio = self._model.generate(
                        text=text,
                        speaker=speaker,
                        context=context,
                        max_audio_length_ms=max_audio_length_ms,
                        temperature=temperature,
                        topk=topk
                    )
            else:
                audio = self._model.generate(
                    text=text,
                    speaker=speaker,
                    context=context,
                    max_audio_length_ms=max_audio_length_ms,
                    temperature=temperature,
                    topk=topk
                )
            
            # Move audio to CPU to free GPU memory
            if self.device == "cuda":
                audio = audio.cpu()
                
            return audio
            
        except Exception as e:
            logger.error(f"Error generating speech: {str(e)}")
            print(f"Error generating speech: {str(e)}")
            raise
    
    def cleanup(self):
        """Clean up memory"""
        if self.device == "cuda":
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
        gc.collect()

def load_csm_generator(device="cpu", use_half_precision=False):
    """Load the CSM generator with memory optimizations"""
    return CSMGenerator(device=device, use_half_precision=use_half_precision)