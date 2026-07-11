import pyaudio
import wave
import tkinter as tk

wavfile = 'author.wav' 

wf = wave.open(wavfile, 'rb')
RATE = wf.getframerate()
WIDTH = wf.getsampwidth()
LEN = wf.getnframes()
CHANNELS = wf.getnchannels()

audiodata = wf.readframes(LEN)
wf.close()

frame = CHANNELS * WIDTH
maxdur = LEN / RATE

start = 0
end = LEN * frame
current = 0

def playback(event=None):
    global start, end, current
    st = startslider.get()
    dur = durationslider.get()

    if st + dur > maxdur:
        dur = maxdur - st
        durationslider.set(dur)

    newstart = int(st * RATE) * frame
    newend = int((st + dur) * RATE) * frame

    start = newstart
    end = newend

    if current < start or current >= end:
        current = start

def callback(indata, framecount, timeinfo, status):

    global current
    read = framecount * frame
    out = b''

    while len(out) < read:

        read_amt = min(read - len(out), end - current)

        out += audiodata[current : current + read_amt]
        current += read_amt

        if current >= end:
            current = start

    return (out, pyaudio.paContinue)

root = tk.Tk()
root.title("Real-Time Audio Clip Looper")


tk.Label(root, text="Start Time").pack()
startslider = tk.Scale(root, from_=0, to=maxdur, resolution=0.05,
                         orient=tk.HORIZONTAL, length=300, command=playback)
startslider.pack()

tk.Label(root, text="Duration").pack()
durationslider = tk.Scale(root, from_=0.1, to=maxdur, resolution=0.05,
                           orient=tk.HORIZONTAL, length=300, command=playback)
durationslider.set(maxdur) 
durationslider.pack()

p = pyaudio.PyAudio()
format = p.get_format_from_width(WIDTH)

stream = p.open(
    format=format,
    channels=CHANNELS,
    rate=RATE,
    output=True,
    stream_callback=callback 
)

stream.start_stream()

root.mainloop()

stream.stop_stream()
stream.close()
p.terminate()