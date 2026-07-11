# playback_speed_procedural.py
# Read a signal from a wave file,
# adjust playback speed dynamically via Tkinter GUI,
# and play the signal using pyaudio.
# Runs procedurally without object-oriented classes.

import os
import numpy as np
import scipy.io.wavfile as scipy_wav
import scipy.signal as signal
import pyaudio
import tkinter as tk
import wave

# ---------------------------------------------------------
# 1. File Setup
# ---------------------------------------------------------
wavfile = 'author.wav'
print('Name of wave file: %s' % wavfile)

# ---------------------------------------------------------
# 2. Read Wave File Properties
# ---------------------------------------------------------
wf = wave.open(wavfile, 'rb')
RATE = wf.getframerate()
WIDTH = wf.getsampwidth()
LEN = wf.getnframes()
CHANNELS = wf.getnchannels()

# Read the ENTIRE audio file into memory to eliminate disk I/O latency
audio_data = wf.readframes(LEN)
wf.close()

print('The file has %d channel(s).'       % CHANNELS)
print('The file has %d frames/second.'    % RATE)
print('The file has %d frames.'           % LEN)
print('The file has %d bytes per sample.' % WIDTH)

BLOCKLEN = 1024
BLOCK_DURATION = 1000.0 * BLOCKLEN/RATE # duration in milliseconds
print('Block length: %d' % BLOCKLEN)
print('Duration of block in milliseconds: %.2f' % BLOCK_DURATION)

# ---------------------------------------------------------
# 3. Global State Variables (Replacing 'self')
# ---------------------------------------------------------
pos = 0.0          # Continuous exact read pointer
last_alpha = 1.0   # Track speed to reset filter state 
zi = None          # Internal state array for the IIR filter

# ---------------------------------------------------------
# 4. Define Audio Processing Function
# ---------------------------------------------------------
def my_audio_callback(in_data, frame_count, time_info, status):
    """
    Called automatically by PyAudio when it needs a new block of audio.
    Uses 'global' to update state variables instead of 'self'.
    """
    global pos, last_alpha, zi, audio_data, LEN, alpha_var
    
    current_alpha = alpha_var.get()

    # Calculate exact bounds of input needed
    start_idx_int = int(np.floor(pos))
    end_pos_continuous = pos + frame_count * current_alpha
    end_idx_int = int(np.ceil(end_pos_continuous))
    
    # +2 bounds margin for linear interpolation calculation
    num_src_samples = (end_idx_int - start_idx_int) + 2 

    # Extract block continuously through end-of-file using modulo
    src_indices = np.arange(start_idx_int, start_idx_int + num_src_samples) % LEN
    src_chunk = audio_data[src_indices]

    # Anti-Aliasing (Low-pass filter triggered when speeding up)
    if current_alpha > 1.0:
        cutoff = min(0.95, 1.0 / current_alpha)
        b, a = signal.butter(4, cutoff, btype='low')
        
        # Reset filter internal state if speed changes abruptly
        if zi is None or abs(current_alpha - last_alpha) > 0.02:
            zi = signal.lfilter_zi(b, a) * src_chunk[0]
            
        src_chunk_filtered, zi = signal.lfilter(b, a, src_chunk, zi=zi)
        last_alpha = current_alpha
    else:
        src_chunk_filtered = src_chunk
        last_alpha = current_alpha
        zi = None # Clear state 

    # Resampling via Manual Linear Interpolation
    out_indices_continuous = pos + np.arange(frame_count) * current_alpha
    out_indices_relative = out_indices_continuous - start_idx_int

    idx_int = np.floor(out_indices_relative).astype(int)
    idx_frac = out_indices_relative - idx_int
    idx_int = np.clip(idx_int, 0, len(src_chunk_filtered) - 2)

    # Blend adjacent samples by the fractional distance
    out_chunk = src_chunk_filtered[idx_int] * (1.0 - idx_frac) + \
                src_chunk_filtered[idx_int + 1] * idx_frac

    # Update continuous pointer 
    pos = end_pos_continuous % LEN

    return (out_chunk.astype(np.float32).tobytes(), pyaudio.paContinue)

# ---------------------------------------------------------
# 5. Tkinter GUI Setup
# ---------------------------------------------------------
root = tk.Tk()
root.title("Real-Time Playback Speed")
root.geometry("400x150")

tk.Label(root, text="Playback Speed (α)", font=("Arial", 12)).pack(pady=10)

alpha_var = tk.DoubleVar(value=1.0)
slider = tk.Scale(
    root, from_=0.5, to=2.0, resolution=0.01, 
    orient=tk.HORIZONTAL, variable=alpha_var, length=300
)
slider.pack()

# ---------------------------------------------------------
# 6. Open Audio Stream & Run Loop
# ---------------------------------------------------------
p = pyaudio.PyAudio()

stream = p.open(
    format = pyaudio.paFloat32,
    channels = CHANNELS,
    rate = RATE,
    input = False,
    output = True,
    frames_per_buffer = BLOCKLEN,
    stream_callback = my_audio_callback
)

stream.start_stream()

def on_close():
    """Handles graceful termination when exiting the GUI."""
    stream.stop_stream()
    stream.close()
    p.terminate()
    root.destroy()
    print('* Finished')

# Hook the window 'X' close button to our termination logic
root.protocol("WM_DELETE_WINDOW", on_close)

# Start the Tkinter event loop (blocks until user closes the window)
root.mainloop()