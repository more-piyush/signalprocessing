import os
import numpy as np
import scipy.io.wavfile as scipy_wav
import scipy.signal as signal
import pyaudio
import tkinter as tk

wavfile = 'author.wav'

RATE, data = scipy_wav.read(wavfile)

if data.dtype == np.int16:
    data = data.astype(np.float32) / (2**15)
elif data.dtype == np.int32:
    data = data.astype(np.float32) / (2**31)

if data.ndim > 1:
    data = data.mean(axis=1)

audio_data = data
LEN = len(audio_data)
CHANNELS = 1
WIDTH = 4 


BLOCKLEN = 1024


pos = 0.0          
alphal = 1.0   
zi = None          

def callback(data, framecount, time, status):

    global pos, alphal , zi, audio_data, LEN, alpha
    
    alphac = alpha.get()

    start = int(np.floor(pos))
    end = int(pos + framecount * alphac)
    

    samples = (end - start) + 2 

    index = np.arange(start, start + samples) % LEN
    array = audio_data[index]

    if alphac > 1.0:
        cutoff = min(0.97, 1.0 / alphac)
        b, a = signal.butter(2, cutoff)

        zi = signal.lfilter_zi(b, a) * array[0]
            
        filtarray, zi = signal.lfilter(b, a, array, zi=zi)
        alphal = alphac
    else:
        filtarray = array
        alphal = alphac
        zi = None 

    indexoverall = pos + np.arange(framecount) * alphac
    indexfit = indexoverall - start

    indexfitlow = np.floor(indexfit).astype(int)
    frac = indexfit - indexfitlow
    i = np.clip(indexfitlow, 0, len(filtarray) - 2)

    arrayout = filtarray[i] * (1.0 - frac) + \
                filtarray[i + 1] * frac

    pos = end % LEN

    return (arrayout.astype(np.float32).tobytes(), pyaudio.paContinue)

root = tk.Tk()
root.title("Playback Speed")

tk.Label(root, text="Playback Speed").pack()

alpha = tk.DoubleVar(value=1.0)
slider = tk.Scale(
    root, from_=0.5, to=2.0, resolution=0.05, 
    orient=tk.HORIZONTAL, variable=alpha, length=300
)
slider.pack()

p = pyaudio.PyAudio()
format = pyaudio.paFloat32

stream = p.open(
    format = format,
    channels = CHANNELS,
    rate = RATE,
    input = False,
    output = True,
    frames_per_buffer = BLOCKLEN,
    stream_callback = callback
)

stream.start_stream()

def onclose():
    stream.stop_stream()
    stream.close()
    p.terminate()
    

root.protocol(onclose)

root.mainloop()
