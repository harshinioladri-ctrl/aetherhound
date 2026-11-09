"""BENIGN test emitter for validating AetherHound on YOUR OWN lab setup.
Modes: wav (offline test files), audio (keyed tone via speaker), cpu (keyed CPU load pulses)."""
import argparse, time, wave, multiprocessing as mp
import numpy as np
from .morse import encode_envelope, CODE

def keyed(text, unit):
    env = encode_envelope(text, 1)  # 1 sample == 1 unit
    return env

def make_wav(a):
    from .sources import SimSource
    s = SimSource(a.fs, 1024, False, None if a.baseline else 3.0, a.message, a.carrier, a.unit)
    n = int(a.seconds * a.fs / 1024); out = np.concatenate([s.read() for _ in range(n)])
    with wave.open(a.out, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(a.fs)
        w.writeframes((np.clip(out, -1, 1) * 32767).astype(np.int16).tobytes())
    print("wrote", a.out)

def play_audio(a):
    import sounddevice as sd
    fs = a.fs; env = encode_envelope(a.message, int(a.unit * fs))
    t = np.arange(len(env)) / fs
    sd.play((0.2 * env * np.sin(2 * np.pi * a.carrier * t)).astype(np.float32), fs); sd.wait()

def _burn(stop):
    while not stop.is_set(): pass

def cpu_pulse(a):
    """Keys CPU load on/off in a Morse pattern (changes fan/thermal behaviour in a lab box)."""
    env = keyed(a.message, 1); procs = []
    for on in env:
        if on:
            stop = mp.Event(); procs = [mp.Process(target=_burn, args=(stop,)) for _ in range(mp.cpu_count())]
            [p.start() for p in procs]; time.sleep(a.unit); stop.set(); [p.join() for p in procs]
        else: time.sleep(a.unit)

def main():
    p = argparse.ArgumentParser(); p.add_argument("mode", choices=["wav", "audio", "cpu"])
    p.add_argument("--message", default="SECRET"); p.add_argument("--fs", type=int, default=48000)
    p.add_argument("--carrier", type=float, default=18000); p.add_argument("--unit", type=float, default=0.12)
    p.add_argument("--out", default="test.wav"); p.add_argument("--seconds", type=float, default=20)
    p.add_argument("--baseline", action="store_true", help="wav: write 'normal' audio without covert tone")
    a = p.parse_args(); {"wav": make_wav, "audio": play_audio, "cpu": cpu_pulse}[a.mode](a)

if __name__ == "__main__": main()
