"""DSP pipeline: windowed FFT (Welch-averaged) -> dB -> max-pooled feature vector.
Accelerated by C++ matrix math (Week 4 deliverable) when compiled.
"""
import numpy as np
from . import cpp_dsp

_W = {}
def _win(n):
    if n not in _W: _W[n] = np.hanning(n)
    return _W[n]

def _idx(n, nbins):
    return np.linspace(0, n, nbins + 1).astype(int)

def features(block, frame, nbins, is_complex=False):
    m = max(1, len(block) // frame)
    seg = np.asarray(block[:m * frame]).reshape(m, frame) * _win(frame)
    X = np.fft.fft(seg, axis=1) if is_complex else np.fft.rfft(seg, axis=1)
    P = (np.abs(X) ** 2).mean(0)
    if is_complex: P = np.fft.fftshift(P)
    db = 10 * np.log10(P + 1e-12)
    return cpp_dsp.max_pool_reduce(db, _idx(len(db), nbins), nbins)

def bin_freqs(fs, center, frame, nbins, is_complex=False):
    if is_complex: f = np.fft.fftshift(np.fft.fftfreq(frame, 1 / fs)) + center
    else: f = np.fft.rfftfreq(frame, 1 / fs)
    i = _idx(len(f), nbins)
    return np.array([f[i[k]:i[k + 1]].mean() for k in range(nbins)])
