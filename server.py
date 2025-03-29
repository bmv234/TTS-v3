from flask import Flask, request, send_file, jsonify, render_template, send_from_directory
from flask_cors import CORS
import io
import threading
import tempfile
import os
import logging
import sys
import torch
import gc
import torchaudio
import time
import uuid
from threading import Thread

# Set PyTorch memory management options
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

# Import CSM modules
sys.path.append('../csm')  # Add the CSM directory to the path
from generator import Segment
from csm_generator import load_csm_generator

# Configure logging to output to console
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Disable Triton compilation
os.environ["NO_TORCH_COMPILE"] = "1"

# Default to CPU if memory issues occur
DEFAULT_DEVICE = "cuda"  # Use GPU by default with memory optimizations

# Initialize Flask app with the current directory as the static folder
app = Flask(__name__, static_url_path='', static_folder='.')
CORS(app)

# Define available voices with their display names
# CSM doesn't have language-specific models like MeloTTS, but we can use different speaker IDs
AVAILABLE_VOICES = {
    'SPEAKER_0': {'name': 'Speaker 0', 'id': 0},
    'SPEAKER_1': {'name': 'Speaker 1', 'id': 1},
    'SPEAKER_2': {'name': 'Speaker 2', 'id': 2},
    'SPEAKER_3': {'name': 'Speaker 3', 'id': 3},
}

# Current CSM generator instance
current_generator = None
generator_lock = threading.Lock()

# Memory optimization settings
memory_optimization_enabled = True

# Job tracking
active_jobs = {}

def get_generator():
    """Get or create CSM generator instance"""
    global current_generator
    
    with generator_lock:
        if current_generator is None:
            logger.info("Initializing CSM generator...")
            
            # Try to use CUDA with memory optimizations if available
            device = DEFAULT_DEVICE
            dtype = torch.float32
            
            # Check if CUDA is available
            if device == "cuda" and not torch.cuda.is_available():
                logger.warning("CUDA requested but not available, falling back to CPU")
                device = "cpu"
            
            logger.info(f"Using device: {device}")
            
            # Load the CSM model
            try:
                # Load model with memory optimizations if using CUDA
                current_generator = load_csm_generator(
                    device=device, 
                    use_half_precision=(device == "cuda" and memory_optimization_enabled)
                )
                logger.info("CSM generator initialized successfully")
            except Exception as e:
                logger.error(f"Error initializing CSM generator: {str(e)}")
                logger.error("Stack trace:", exc_info=True)
                raise
                
    return current_generator

def cleanup_memory():
    """Clean up memory after generation"""
    if torch.cuda.is_available():
        if current_generator:
            current_generator.cleanup()
        torch.cuda.empty_cache()
    gc.collect()

@app.route('/memory-settings', methods=['POST'])
def update_memory_settings():
    """Update memory optimization settings"""
    global memory_optimization_enabled, DEFAULT_DEVICE, current_generator
    
    data = request.json
    if 'optimization' in data:
        memory_optimization_enabled = bool(data['optimization'])
    if 'device' in data:
        DEFAULT_DEVICE = data['device']
    
    # Reset generator to apply new settings
    with generator_lock:
        current_generator = None
        cleanup_memory()
        
    return jsonify({'success': True, 'optimization': memory_optimization_enabled, 'device': DEFAULT_DEVICE})

@app.route('/voices', methods=['GET'])
def list_voices():
    """List available voices"""
    try:
        voices = [
            {'id': k, 'name': v['name']} 
            for k, v in AVAILABLE_VOICES.items()
        ]
        logger.info(f"Available voices: {voices}")
        return jsonify({'voices': voices})
    except Exception as e:
        logger.error(f"Error in list_voices: {str(e)}")
        logger.error("Stack trace:", exc_info=True)
        return jsonify({'error': str(e)}), 500
        
def generate_speech_task(job_id, text, speaker_id, speed):
    """Background task for speech generation"""
    try:
        # Get CSM generator
        generator = get_generator()

        # Ensure we have clean memory before generation
        cleanup_memory()
        
        # Update job status
        active_jobs[job_id]['status'] = 'generating'
        
        # Generate speech with CSM
        audio = generator.generate(
            text=text,
            speaker=speaker_id,
            context=[],  # Empty context
            max_audio_length_ms=20_000,  # 20 seconds max
            temperature=0.9,  # Default temperature
            topk=50,  # Default topk
        )
        
        # Apply speed modification if needed
        if speed != 1.0:
            # Resample the audio to change the speed
            orig_length = audio.shape[0]
            target_length = int(orig_length / speed)
            audio = torchaudio.functional.resample(
                audio, 
                orig_freq=generator.sample_rate, 
                new_freq=int(generator.sample_rate * speed)
            )
        
        # Create a temporary file to store the audio
        temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        temp_path = temp_file.name
        temp_file.close()
        
        # Save the audio to the temporary file
        torchaudio.save(
            temp_path,
            audio.unsqueeze(0).cpu(),
            generator.sample_rate
        )
        
        # Update job status with file path
        active_jobs[job_id]['status'] = 'completed'
        active_jobs[job_id]['file_path'] = temp_path
        active_jobs[job_id]['sample_rate'] = generator.sample_rate
        
    except Exception as e:
        logger.error(f"Error in speech generation task: {str(e)}")
        logger.error("Stack trace:", exc_info=True)
        active_jobs[job_id]['status'] = 'error'
        active_jobs[job_id]['error'] = str(e)
    finally:
        # Clean up memory
        cleanup_memory()

@app.route('/synthesize', methods=['POST'])
def synthesize():
    try:
        data = request.json
        if not data or 'text' not in data:
            return jsonify({'error': 'No text provided'}), 400

        text = data['text']
        speed = float(data.get('speed', 1.0))
        voice_id = data.get('voice', 'SPEAKER_0')  # Default to SPEAKER_0 if not specified
        
        # Get the speaker ID for the voice
        voice_info = AVAILABLE_VOICES.get(voice_id)
        if not voice_info:
            return jsonify({'error': f'Invalid voice ID: {voice_id}'}), 400
            
        speaker_id = voice_info['id']
        
        # Limit text length to prevent OOM errors
        if len(text) > 500:
            logger.warning(f"Text too long ({len(text)} chars), truncating to 500 chars")
            text = text[:500]
        
        logger.info(f"Synthesizing text: {text} with speed: {speed} using voice: {voice_id} (speaker ID: {speaker_id})")

        # Create a job ID
        job_id = str(uuid.uuid4())
        
        # Create a job entry
        active_jobs[job_id] = {
            'status': 'queued',
            'text': text,
            'speaker_id': speaker_id,
            'speed': speed,
            'created_at': time.time()
        }
        
        # Start a background thread for generation
        thread = Thread(
            target=generate_speech_task,
            args=(job_id, text, speaker_id, speed)
        )
        thread.daemon = True
        thread.start()
        
        # Return the job ID immediately
        return jsonify({
            'job_id': job_id,
            'status': 'queued'
        })
            
    except Exception as e:
        logger.error(f"Error in synthesis: {str(e)}")
        logger.error("Stack trace:", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/job/<job_id>', methods=['GET'])
def get_job_status(job_id):
    """Get the status of a speech generation job"""
    try:
        if job_id not in active_jobs:
            return jsonify({'error': 'Job not found'}), 404
            
        job = active_jobs[job_id]
        
        # If job is completed, return the audio file
        if job['status'] == 'completed' and request.args.get('download') == 'true':
            file_path = job['file_path']
            
            if not os.path.exists(file_path):
                return jsonify({'error': 'Audio file not found'}), 404
                
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                return jsonify({'error': 'Audio file is empty'}), 500
                
            # Send the file
            response = send_file(
                file_path,
                mimetype='audio/wav',
                as_attachment=True,
                download_name='speech.wav'
            )
            
            # Add content length header
            response.headers['Content-Length'] = file_size
            return response
            
        # Otherwise just return the status
        return jsonify({
            'job_id': job_id,
            'status': job['status'],
            'created_at': job['created_at'],
            'error': job.get('error')
        })
        
    except Exception as e:
        logger.error(f"Error getting job status: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/cleanup', methods=['POST'])
def cleanup_jobs():
    """Clean up completed jobs"""
    try:
        # Get jobs to clean up
        job_ids = request.json.get('job_ids', [])
        
        cleaned = 0
        for job_id in job_ids:
            if job_id in active_jobs and active_jobs[job_id]['status'] == 'completed':
                # Delete the audio file
                file_path = active_jobs[job_id].get('file_path')
                if file_path and os.path.exists(file_path):
                    os.unlink(file_path)
                
                # Remove the job
                del active_jobs[job_id]
                cleaned += 1
                
        # Also clean up old jobs (older than 30 minutes)
        current_time = time.time()
        old_jobs = []
        for job_id, job in active_jobs.items():
            if current_time - job['created_at'] > 1800:  # 30 minutes
                old_jobs.append(job_id)
                
        for job_id in old_jobs:
            # Delete the audio file
            file_path = active_jobs[job_id].get('file_path')
            if file_path and os.path.exists(file_path):
                os.unlink(file_path)
            
            # Remove the job
            del active_jobs[job_id]
            cleaned += 1
        
        return jsonify({'cleaned': cleaned})
        
    except Exception as e:
        logger.error(f"Error cleaning up jobs: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/status', methods=['GET'])
def get_status():
    """Get server status and memory information"""
    try:
        status = {
            'device': DEFAULT_DEVICE,
            'memory_optimization': memory_optimization_enabled,
            'model_loaded': current_generator is not None
        }
        
        if torch.cuda.is_available():
            free_memory = torch.cuda.get_device_properties(0).total_memory - torch.cuda.memory_allocated(0)
            free_memory_gb = free_memory / (1024**3)
            status['gpu_memory'] = {
                'total_gb': torch.cuda.get_device_properties(0).total_memory / (1024**3),
                'used_gb': torch.cuda.memory_allocated(0) / (1024**3),
                'free_gb': free_memory_gb
            }
            
        return jsonify(status)
    except Exception as e:
        logger.error(f"Error in get_status: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/')
def index():
    """Serve the main HTML page"""
    return send_from_directory('.', 'index.html')

if __name__ == '__main__':
    logger.info("Starting CSM TTS server...")
    try:
        # Print memory optimization status
        logger.info(f"Memory optimization: {'Enabled' if memory_optimization_enabled else 'Disabled'}")
        logger.info(f"Default device: {DEFAULT_DEVICE}")
        
        # Pre-load the generator to avoid first-request delay
        try:
            get_generator()
        except Exception as e:
            logger.error(f"Failed to pre-load generator: {str(e)}")
            logger.info("Server will continue running, but model will be loaded on first request")
            
        app.run(host='0.0.0.0', port=5000, debug=True)
    except Exception as e:
        logger.error(f"Error starting server: {str(e)}")
        logger.error("Stack trace:", exc_info=True)
        sys.exit(1)