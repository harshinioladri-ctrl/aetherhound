# AetherHound GNU Radio DSP Pipeline

This directory contains the Week 2 Digital Signal Processing (DSP) flowgraphs for filtering server room noise and streaming spectrogram matrices to the AetherHound ML detector.

## Architecture

```
[ Ultrasonic Mic / SDR ]
         │
         ▼
[ Bandpass Filter ] (Suppresses 50/60 Hz mains hum & high-freq noise)
         │
         ▼
[ Stream to Vector ] (Block size = 1024)
         │
         ▼
[ Blackman-Harris Windowed FFT ]
         │
         ▼
[ Complex to Mag^2 ] (Power Spectral Density)
         │
         ▼
[ 10*log10 ] (Logarithmic dB Spectrogram)
         │
         ▼
[ UDP Sink (127.0.0.1:9090) ] ──> AetherHound ML Autoencoder
```

## Running the GNU Radio DSP Pipeline
1. Using GNU Radio Companion:
   ```bash
   gnuradio-companion aetherhound_sdr.grc
   ```
2. Using the standalone Python pipeline:
   ```bash
   python gnuradio/aetherhound_dsp.py
   ```
3. Connecting AetherHound to the GNU Radio stream:
   ```bash
   python -m aetherhound run --source gnuradio:udp://127.0.0.1:9090
   ```
