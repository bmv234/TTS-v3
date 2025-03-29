document.addEventListener('DOMContentLoaded', () => {
    const textInput = document.getElementById('textInput');
    const playButton = document.getElementById('playButton');
    const volumeControl = document.getElementById('volumeControl');
    const speedControl = document.getElementById('speedControl');
    const voiceSelect = document.getElementById('voiceSelect');
    const darkModeToggle = document.getElementById('darkModeToggle');
    const highlightedText = document.getElementById('highlightedText');
    const settingsButton = document.getElementById('settingsButton');
    const settingsPanel = document.getElementById('settingsPanel');
    const deviceSelect = document.getElementById('deviceSelect');
    const memoryOptimization = document.getElementById('memoryOptimization');
    const applySettings = document.getElementById('applySettings');
    const settingsStatus = document.getElementById('settingsStatus');
    const progressContainer = document.getElementById('progressContainer');
    const progressBar = document.getElementById('progressBar');
    const progressText = document.getElementById('progressText');
    
    let isPlaying = false;
    let isGenerating = false;
    let currentAudio = null;
    let currentJobId = null;
    let jobCheckInterval = null;
    let serverStatus = null;

    // Check for saved dark mode preference
    if (localStorage.getItem('darkMode') === 'true') {
        document.body.classList.add('dark-mode');
        darkModeToggle.querySelector('.toggle-icon').textContent = '☀️';
    }

    // Dark mode toggle
    darkModeToggle.addEventListener('click', () => {
        document.body.classList.toggle('dark-mode');
        const isDarkMode = document.body.classList.contains('dark-mode');
        darkModeToggle.querySelector('.toggle-icon').textContent = isDarkMode ? '☀️' : '🌙';
        localStorage.setItem('darkMode', isDarkMode);
    });

    // Settings panel toggle
    settingsButton.addEventListener('click', () => {
        settingsPanel.classList.toggle('hidden');
        // Fetch current server status when opening settings
        if (!settingsPanel.classList.contains('hidden')) {
            fetchServerStatus();
        }
    });

    // Apply settings button
    applySettings.addEventListener('click', async () => {
        const device = deviceSelect.value;
        const optimization = memoryOptimization.checked;
        const apiUrl = window.location.origin;
        
        settingsStatus.textContent = "Applying settings...";
        
        try {
            const response = await fetch(`${apiUrl}/memory-settings`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    device: device,
                    optimization: optimization
                })
            });
            
            if (!response.ok) {
                throw new Error('Failed to update settings');
            }
            
            const result = await response.json();
            settingsStatus.textContent = "Settings applied successfully!";
            
            // Update server status
            fetchServerStatus();
            
            // Clear status after 3 seconds
            setTimeout(() => {
                settingsStatus.textContent = "";
            }, 3000);
            
        } catch (error) {
            console.error('Error applying settings:', error);
            settingsStatus.textContent = `Error: ${error.message}`;
        }
    });

    // Fetch server status
    async function fetchServerStatus() {
        try {
            const apiUrl = window.location.origin;
            const response = await fetch(`${apiUrl}/status`);
            if (!response.ok) throw new Error('Failed to fetch server status');
            
            serverStatus = await response.json();
            
            // Update UI based on server status
            deviceSelect.value = serverStatus.device;
            memoryOptimization.checked = serverStatus.memory_optimization;
            
            // Display GPU memory info if available
            if (serverStatus.gpu_memory) {
                const memInfo = serverStatus.gpu_memory;
                const memoryInfo = document.createElement('div');
                memoryInfo.className = 'settings-info';
                memoryInfo.textContent = `GPU Memory: ${memInfo.free_gb.toFixed(2)}GB free / ${memInfo.total_gb.toFixed(2)}GB total`;
                
                // Replace existing memory info if present
                const existingInfo = settingsPanel.querySelector('.memory-info');
                if (existingInfo) {
                    existingInfo.remove();
                }
                
                memoryInfo.classList.add('memory-info');
                settingsPanel.appendChild(memoryInfo);
            }
            
        } catch (error) {
            console.error('Error fetching server status:', error);
        }
    }

    // Function to create word spans for highlighting
    function createWordSpans(text) {
        highlightedText.innerHTML = text.split(' ').map(word => 
            `<span class="word">${word}</span>`
        ).join(' ');
    }

    // Update highlighted text when input changes
    textInput.addEventListener('input', () => {
        createWordSpans(textInput.value);
    });

    // Function to stop current playback
    function stopPlayback() {
        if (currentAudio) {
            currentAudio.pause();
            currentAudio = null;
        }
        isPlaying = false;
        updatePlayButtonState();
        
        // Remove all highlights
        const words = Array.from(highlightedText.getElementsByClassName('word'));
        words.forEach(word => word.classList.remove('highlighted'));
    }

    // Function to update play button state
    function updatePlayButtonState() {
        const btnIcon = playButton.querySelector('.btn-icon');
        
        // Remove any existing loading indicator
        const existingLoader = playButton.querySelector('.loading');
        if (existingLoader) {
            existingLoader.remove();
        }
        
        if (isGenerating) {
            btnIcon.textContent = '⏳';
            // Add loading spinner
            const loader = document.createElement('span');
            loader.className = 'loading';
            playButton.appendChild(loader);
            playButton.disabled = true;
        } else if (isPlaying) {
            btnIcon.textContent = '⏹';
            playButton.disabled = false;
        } else {
            btnIcon.textContent = '▶';
            playButton.disabled = false;
        }
    }

    // Function to poll job status
    async function pollJobStatus(jobId) {
        try {
            const apiUrl = window.location.origin;
            const response = await fetch(`${apiUrl}/job/${jobId}`);
            
            if (!response.ok) {
                throw new Error('Failed to get job status');
            }
            
            const jobStatus = await response.json();
            
            // Update UI based on job status
            if (jobStatus.status === 'completed') {
                // Job is complete, download the audio
                clearInterval(jobCheckInterval);
                await downloadAndPlayAudio(jobId);
            } else if (jobStatus.status === 'error') {
                // Job failed
                clearInterval(jobCheckInterval);
                highlightedText.innerHTML = `<p style="color: red;">Error: ${jobStatus.error || 'Failed to generate speech'}</p>`;
                
                // Hide progress
                progressContainer.classList.add('hidden');
                
                isGenerating = false;
                updatePlayButtonState();
            } else {
                // Job is still processing, update the UI
                const elapsedTime = Math.floor((Date.now() - (jobStatus.created_at * 1000)) / 1000);
                
                // Update progress bar (simulate progress)
                // Since we don't know the actual progress, we'll simulate it
                // Cap at 90% until complete
                const simulatedProgress = Math.min(90, elapsedTime * 2);
                progressBar.style.width = `${simulatedProgress}%`;
                progressText.textContent = `Generating speech... (${elapsedTime}s)`;
                
                // Show progress container if not already visible
                if (progressContainer.classList.contains('hidden')) {
                    progressContainer.classList.remove('hidden');
                }
                
                highlightedText.innerHTML = `<p>Processing text: "${textInput.value.substring(0, 50)}${textInput.value.length > 50 ? '...' : ''}"</p>
                                            <p>This may take 1-2 minutes on CPU. Please be patient.</p>`;
            }
            
        } catch (error) {
            console.error('Error polling job status:', error);
            // Don't stop polling on network errors, as they might be temporary
        }
    }
    
    // Function to download and play audio
    async function downloadAndPlayAudio(jobId) {
        try {
            const apiUrl = window.location.origin;
            const response = await fetch(`${apiUrl}/job/${jobId}?download=true`);
            
            if (!response.ok) {
                throw new Error('Failed to download audio');
            }
            
            const audioBlob = await response.blob();
            const audioUrl = URL.createObjectURL(audioBlob);
            
            // Complete the progress bar
            progressBar.style.width = '100%';
            progressText.textContent = 'Speech generated successfully!';
            
            // Hide progress after a delay
            setTimeout(() => {
                progressContainer.classList.add('hidden');
                // Reset progress bar
                progressBar.style.width = '0%';
            }, 1500);
            
            // Reset the generation state
            isGenerating = false;
            isPlaying = true;
            updatePlayButtonState();
            
            // Create word spans for highlighting
            const text = textInput.value.trim();
            createWordSpans(text);
            const words = Array.from(highlightedText.getElementsByClassName('word'));
            
            currentAudio = new Audio(audioUrl);
            currentAudio.volume = parseFloat(volumeControl.value);
            
            currentAudio.addEventListener('loadedmetadata', () => {
                const timePerWord = (currentAudio.duration * 1000) / words.length;
                
                currentAudio.play();

                // Word highlighting
                let currentWordIndex = 0;
                const highlightInterval = setInterval(() => {
                    if (!isPlaying || currentWordIndex >= words.length) {
                        clearInterval(highlightInterval);
                        return;
                    }

                    // Remove previous highlight
                    if (currentWordIndex > 0) {
                        words[currentWordIndex - 1].classList.remove('highlighted');
                    }
                    
                    // Add new highlight
                    words[currentWordIndex].classList.add('highlighted');
                    currentWordIndex++;
                }, timePerWord);

                currentAudio.onended = () => {
                    stopPlayback();
                    clearInterval(highlightInterval);
                    
                    // Clean up the job
                    cleanupJob(jobId);
                };
            });
            
        } catch (error) {
            console.error('Error downloading audio:', error);
            highlightedText.innerHTML = `<p style="color: red;">Error: ${error.message || 'Failed to download audio'}</p>`;
            
            // Hide progress
            progressContainer.classList.add('hidden');
            
            isGenerating = false;
            updatePlayButtonState();
        }
    }
    
    // Function to clean up completed job
    async function cleanupJob(jobId) {
        try {
            const apiUrl = window.location.origin;
            await fetch(`${apiUrl}/cleanup`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    job_ids: [jobId]
                })
            });
        } catch (error) {
            console.error('Error cleaning up job:', error);
        }
    }

    // Play button click handler
    playButton.addEventListener('click', async () => {
        if (isGenerating) return; // Prevent multiple clicks during generation
        
        if (isPlaying) {
            stopPlayback();
            return;
        }

        const text = textInput.value.trim();
        if (!text) {
            alert('Please enter some text to synthesize');
            return;
        }

        // Stop any existing polling
        if (jobCheckInterval) {
            clearInterval(jobCheckInterval);
            jobCheckInterval = null;
        }

        isGenerating = true;
        updatePlayButtonState();
        
        // Reset and show progress container
        progressBar.style.width = '0%';
        progressText.textContent = 'Starting speech generation...';
        progressContainer.classList.remove('hidden');
        
        try {
            // Show a message in the highlighted text area
            highlightedText.innerHTML = '<p>Generating speech with CSM... This may take a minute or two on CPU. Please be patient.</p>';
            
            // If we have server status and it shows low GPU memory, show a warning
            if (serverStatus && serverStatus.gpu_memory && serverStatus.gpu_memory.free_gb < 1.0 && serverStatus.device === 'cuda') {
                highlightedText.innerHTML += '<p style="color: orange;">Warning: Low GPU memory detected. If generation fails, try switching to CPU mode in settings.</p>';
            }
            
            const apiUrl = window.location.origin;
            const response = await fetch(`${apiUrl}/synthesize`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    text: text,
                    speed: parseFloat(speedControl.value),
                    voice: voiceSelect.value
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Speech generation failed');
            }

            const jobData = await response.json();
            currentJobId = jobData.job_id;
            
            // Start polling for job status
            highlightedText.innerHTML = '<p>Generating speech with CSM... This may take a minute or two on CPU. Please be patient.</p>';
            jobCheckInterval = setInterval(() => pollJobStatus(currentJobId), 1000);

        } catch (error) {
            console.error('Error:', error);
            
            // Hide progress
            progressContainer.classList.add('hidden');
            
            let errorMessage = error.message || 'Failed to generate speech';
            
            // Check if it's an out of memory error
            if (errorMessage.includes('out of memory') || errorMessage.includes('CUDA')) {
                errorMessage += '<br><br>Suggestion: Try switching to CPU mode in settings ⚙️ or reduce text length.';
            }
            
            highlightedText.innerHTML = `<p style="color: red;">Error: ${errorMessage}</p>`;
            isGenerating = false;
            updatePlayButtonState();
        }
    });

    // Volume control
    volumeControl.addEventListener('input', (e) => {
        const volume = parseFloat(e.target.value);
        if (currentAudio) {
            currentAudio.volume = volume;
        }
    });

    // Speed control - Note: This only affects client-side playback speed
    // The actual generation speed is controlled by the server
    speedControl.addEventListener('input', (e) => {
        const speed = parseFloat(e.target.value);
        if (currentAudio) {
            currentAudio.playbackRate = speed;
        }
    });

    // Fetch available voices from the server
    async function fetchVoices() {
        try {
            const apiUrl = window.location.origin;
            const response = await fetch(`${apiUrl}/voices`);
            if (!response.ok) throw new Error('Failed to fetch voices');
            
            const data = await response.json();
            if (data.voices && data.voices.length > 0) {
                // Clear existing options
                voiceSelect.innerHTML = '';
                
                // Add new options
                data.voices.forEach(voice => {
                    const option = document.createElement('option');
                    option.value = voice.id;
                    option.textContent = voice.name;
                    voiceSelect.appendChild(option);
                });
            }
        } catch (error) {
            console.error('Error fetching voices:', error);
        }
    }

    // Initialize the app
    fetchVoices().catch(console.error);
    
    // Fetch initial server status
    fetchServerStatus().catch(console.error);
    
    // Add keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        // Space bar to play/pause when not typing in the textarea
        if (e.code === 'Space' && document.activeElement !== textInput) {
            e.preventDefault();
            playButton.click();
        }
        
        // Escape to stop playback
        if (e.code === 'Escape' && isPlaying) {
            stopPlayback();
        }
    });
});