# INTERNSHIP PROJECT REPORT

## PROJECT 2: "AetherHound" — Air-Gapped RF & Acoustic Covert Channel Detector

---

| **Internship Organization** | Infotact Solutions (ISO 9001:2015 Certified) |
|---|---|
| **Location** | Electronic City, Bengaluru, Karnataka, India |
| **Project Title** | AetherHound: Air-Gapped RF & Acoustic Covert Channel Detector |
| **Domain** | Hardware Security / Signals Intelligence (SIGINT) / Machine Learning |
| **Target Infrastructure** | Isolated High-Security Air-Gapped Server Rooms & SCADA Networks |

---

## ABSTRACT

In highly classified corporate and government defense environments, mission-critical compute infrastructure is physically isolated from external networks—a defensive paradigm known as "air-gapping." Despite the lack of network interfaces, advanced persistent threats (APTs) can exfiltrate sensitive secrets (encryption keys, credentials, telemetry) by modulating physical hardware emissions. Malware running on compromised nodes can manipulate CPU fan speeds (generating acoustic Morse pulses) or modulate high-speed RAM and bus memory access (radiating electromagnetic RF pulses) to leak data to covert receivers.

This report presents **AetherHound**, a defensive Signals Intelligence (SIGINT) hardware-software monitoring array designed to detect, isolate, demodulate, and log air-gap covert channel exfiltration in real time. Deployed on an edge platform (Raspberry Pi combined with HackRF One SDR and ultrasonic microphone arrays), AetherHound utilizes:
1. A real-time Digital Signal Processing (DSP) pipeline (accelerated in C++ with GNU Radio flowgraphs) computing windowed Welch Power Spectral Density (PSD) matrices;
2. An unsupervised Deep Autoencoder Neural Network (PyTorch) trained solely on nominal server room ambient acoustic and RF emissions;
3. A Peak-to-Average Power Ratio (PAPR) spectral flatness filter and persistence detector to eliminate false positives from ambient industrial transients;
4. An automated On-Off Keying (OOK) / Morse code demodulation engine that reconstructs exfiltrated plain text.

During evaluation, AetherHound achieved **2399+ FPS** processing throughput (exceeding the 30 FPS requirement by 80x), demonstrated **0% false alarms** on baseline server room hum, isolated malware fan carrier spikes with **100% precision**, and accurately decoded exfiltrated covert payloads.

---

## 1. INTRODUCTION & THREAT MODEL

### 1.1 The Air-Gap Paradigm
Air-gapped systems are intentionally isolated from the Internet, local area networks, Wi-Fi, and Bluetooth. Historically, air-gapping was considered an impenetrable perimeter against remote data theft.

### 1.2 State-of-the-Art Covert Channel Attacks
Academic and intelligence research has repeatedly demonstrated physical side-channel exfiltration from air-gapped computers:
- **Fansmitter (Acoustic)**: Malware manipulates CPU load or PWM fan controllers to modulate the mechanical blade-passing frequency (BPF) of cooling fans, transmitting Morse or FSK audio to an eavesdropper's microphone.
- **AirHopper (Electromagnetic)**: Malware periodically writes to video RAM or memory buses, causing memory buses to act as unintended transmission antennas radiating RF signals in the FM/VHF/UHF bands.
- **RAMBO & GSMem**: Exfiltration via RAM bus clock oscillations and cellular frequencies.

### 1.3 The AetherHound Defensive Solution
Existing Intrusion Detection Systems (IDS) inspect network packets or OS system calls. AetherHound introduces **Physical Air-Gap SIGINT Monitoring**: continuously monitoring the RF and acoustic electromagnetic spectrum of the server room. By learning the room's baseline "hum" with an Autoencoder, any artificial, structured pulsing is immediately detected and localized.

---

## 2. SYSTEM ARCHITECTURE & KEY MODULES

```
       ┌────────────────────────────────────────────────────────┐
       │             Layer 1: Sensor & Capture Array            │
       │   - HackRF One (1 MHz - 6 GHz Software Defined Radio)  │
       │   - Ultrasonic Condenser Microphones (up to 48/96 kHz) │
       │   - PyAudio / SoundDevice / RTL-SDR / SimReplay        │
       └───────────────────────────┬────────────────────────────┘
                                   │ Raw ADC / I-Q Samples
                                   ▼
       ┌────────────────────────────────────────────────────────┐
       │         Layer 2: Digital Signal Processing (DSP)       │
       │   - GNU Radio Top Block Filter (50/60 Hz Hum Rejection)│
       │   - Windowed Fast Fourier Transform (Hanning Window)   │
       │   - Welch Power Spectral Density (PSD) Averaging       │
       │   - Max-Pooling Sub-Band Reduction (64 Bins)           │
       │   - Accelerated Native C++ Matrix Core (C++17)         │
       └───────────────────────────┬────────────────────────────┘
                                   │ Logarithmic dB Feature Vector [64]
                                   ▼
       ┌────────────────────────────────────────────────────────┐
       │     Layer 3: Anomaly Autoencoder (PyTorch / Stat)      │
       │   - Deep Autoencoder: 64 -> 48 -> 12 (Bottleneck) -> 64│
       │   - Reconstruction Residual: R(z) = |z - net(z)|       │
       │   - Top-K Residual Anomaly Score & Dynamic Threshold   │
       │   - PAPR Broadband Transient Rejection Filter          │
       │   - Exponential Moving Average (EMA) Baseline Drift    │
       └───────────────────────────┬────────────────────────────┘
                                   │ Anomaly Trigger & Offending Bin
                                   ▼
       ┌────────────────────────────────────────────────────────┐
       │      Layer 4: Demodulation, Alerting & Forensics       │
       │   - On-Off Keying (OOK) Pulse Width Estimation         │
       │   - Morse Code Demodulation Engine -> ASCII Text       │
       │   - Real-Time Hacker Curses / ANSI Spectrum Waterfall  │
       │   - GPIO Buzzer / Hardware Bell / SIEM JSONL & CSV Logs│
       └────────────────────────────────────────────────────────┘
```

---

## 3. WEEK-WISE IMPLEMENTATION LOG

### Week 1: Hardware Layer & Mock Malware Development
- **Hardware Integration (`aetherhound/sources.py`, `aetherhound/record.py`)**:
  - Implemented multi-backend audio stream capture using `pyaudio` and `sounddevice`.
  - Integrated `pyrtlsdr` and `SoapySDR` for HackRF One high-bandwidth RF acquisition.
  - Implemented standalone recording utility (`aetherhound record`) generating `.wav`, `.raw`, and `.npy` datasets with JSON metadata.
- **Benign Mock Malware (`aetherhound/mock_malware.py`)**:
  - Engineered CPU fan modulation harness mimicking *Fansmitter*.
  - Saturated multi-core processing threads in controlled Morse code pulse widths (`.` = 1 unit, `-` = 3 units).
  - Implemented physical acoustic fan Doppler synthesizer modeling 7-blade server fan acceleration from 2400 RPM baseline to 3600 RPM peak.

### Week 2: DSP Flowgraph & Live Terminal CLI
- **DSP Flowgraph (`gnuradio/aetherhound_dsp.py`, `gnuradio/aetherhound_sdr.grc`)**:
  - Created GNU Radio flowgraph incorporating bandpass filtering, Blackman-Harris windowing, FFT computation, and UDP matrix transmission.
  - Implemented Python Welch PSD averaging and max-pooling reduction into 64 uniform sub-bands.
- **Hacker-Style Waterfall CLI (`aetherhound/ui.py`)**:
  - Developed full-screen live terminal waterfall with ANSI/Curses color heatmaps (` .:-=+*#%@`).
  - Added real-time score bar, anomaly alert banners, and target frequency marker `^`.
  - Provided graceful fallback to high-speed ANSI live streaming for non-interactive headless terminals.

### Mid-Project Review: Capture Validation & UI Benchmarking
- **Capture Validation (`aetherhound/validate_capture.py`)**:
  - Injected mock fan malware carrier at 18.0 kHz with Morse payload `"FAN 007"`.
  - Proved that the system isolates the exact frequency bin (Bin 48 @ 18.16 kHz) with zero deviation outside the bin resolution.
  - Decoded the Morse payload with 100% accuracy.
- **UI & DSP Performance Benchmark (`aetherhound/benchmark.py`)**:
  - Benchmark requirement: **>= 30 FPS**.
  - Benchmarked across 1,000 real-time streaming frames:
    - Average DSP time per frame: **0.084 ms**
    - Average ML inference time per frame: **0.190 ms**
    - Achieved throughput: **2,399.7 FPS** (Exceeded requirement by ~80x).

### Week 3: ML Training & Alerting Subsystem
- **Deep Autoencoder (`aetherhound/models.py`)**:
  - Architecture: Input (64) $\to$ Linear(48) $\to$ BatchNorm $\to$ ReLU $\to$ Bottleneck Linear(12) $\to$ Linear(48) $\to$ BatchNorm $\to$ Output Linear(64).
  - Trained unsupervised strictly on nominal server room emissions using AdamW optimizer and Cosine Annealing learning rate schedule.
  - Nominal signals reconstruct with MSE $< 0.05$; structured covert pulses produce localized reconstruction errors exceeding the calibrated 99.9th percentile threshold.
- **Multi-Server Hum Dataset Generator (`aetherhound/dataset.py`)**:
  - Synthesizes realistic 24-hour server room hum: 50/60 Hz electrical mains, dual cooling fan aerodynamic blade passing frequencies, power supply coil whine (19.2 kHz), and random hard disk seek clicks.
- **Alerting Logic (`aetherhound/alerts.py`)**:
  - Real-time audible buzzer trigger using Windows `winsound.Beep` and Raspberry Pi GPIO (`gpiozero.Buzzer`).
  - Terminal visual flashing and bell notifications.

### Week 4: Native C++ Acceleration, False-Positive Tuning & Polish
- **Native C++ DSP Core (`src_cpp/dsp_core.cpp`, `aetherhound/cpp_dsp.py`)**:
  - Ported heavy matrix operations (Hanning windowing, Welch power spectrum, max-pooling reduction, top-k scoring) to pure C++17 with OpenMP support.
  - Created dynamic ctypes wrapper loading `aetherhound_dsp.dll` / `libaetherhound_dsp.so` with zero-dependency NumPy fallback.
- **False-Positive Tuning (`aetherhound/detector.py`)**:
  - **PAPR Spectral Flatness Filter**: Calculates Peak-to-Average Power Ratio across the spectrum. Rejects wideband acoustic transients (door slams, coughing, chair scraping) where energy is spread evenly, while preserving narrowband covert channels.
  - **Persistence Filter**: Mandates $N \ge 4$ consecutive frames above threshold before state transition.
  - **Adaptive EMA Drift Tracker**: Adjusts $\mu$ and $\sigma^2$ using Exponential Moving Average ($\alpha = 0.0005$) during quiet periods to track server room seasonal/diurnal thermal shifts.
- **Forensic Reporting (`aetherhound/report.py`)**:
  - Timestamped incident recording in both JSONL and CSV formats.
  - Standalone HTML forensic incident report generator (`logs/incident_report.html`) with incident chronology and decoded exfiltrations.

---

## 4. MATHEMATICAL FORMULATION

### 4.1 Welch Power Spectral Density (PSD)
For raw time-domain block $x[n]$ segmented into $M$ sub-frames of length $L$ with window $w[n]$:
$$X_m[k] = \sum_{n=0}^{L-1} x_m[n] w[n] e^{-j \frac{2\pi}{L} k n}$$
$$P[k] = \frac{1}{M} \sum_{m=0}^{M-1} |X_m[k]|^2$$
$$P_{\text{dB}}[k] = 10 \log_{10}(P[k] + 10^{-12})$$

### 4.2 Autoencoder Reconstruction & Top-K Scoring
Normalized feature vector:
$$z = \frac{f - \mu}{\sqrt{\sigma^2}}$$
Reconstruction residual:
$$r = z - \text{Decoder}(\text{Encoder}(z))$$
Top-$K$ residual anomaly score:
$$\text{Score}(r) = \frac{1}{K} \sum_{i \in \text{TopK}} (r_i \cdot \text{Mask}_i)^2$$

### 4.3 Peak-to-Average Power Ratio (PAPR) Filter
$$\text{PAPR} = \frac{\max(z)}{\frac{1}{N}\sum_{i=1}^{N} z_i}$$
$$\text{If } \text{PAPR} < 2.5 \implies \text{Transient Room Noise (Door Slam) } \implies \text{Reject}$$

---

## 5. EXPERIMENTAL RESULTS & VALIDATION

| Evaluation Metric | Target / Requirement | AetherHound Measured Performance | Result |
|---|---|---|:---:|
| **Processing Throughput** | $\ge 30.0$ FPS | **2,399.7 FPS** | **PASS** (80x faster) |
| **Average Latency / Frame** | $< 33.3$ ms | **0.416 ms** | **PASS** |
| **Malware Spike Isolation** | Target Bin Resolution | **Exact Bin 48 Isolated (18.16 kHz)** | **PASS** |
| **Morse Demodulation Accuracy** | Correct Text Decoding | **100% Exact Match ("FAN 007")** | **PASS** |
| **False Positive Rate (Baseline)** | 0 false alarms / 10 min | **0 False Positives** | **PASS** |
| **Transient Noise Rejection** | Rejection of Wideband Impulses | **100% Door Slam / Noise Rejection** | **PASS** |

---

## 6. CONCLUSION & FUTURE DIRECTIONS

The AetherHound project demonstrates that physical-layer side-channel exfiltration from air-gapped computers can be reliably detected, pinpointed, and decoded using low-cost edge hardware, digital signal processing, and unsupervised machine learning. By combining Deep Autoencoders with physical signal characteristics (PAPR and persistence filtering), the system achieves near-zero false alarms while running at thousands of frames per second.

### Future Work
1. **Multi-Microphone Direction of Arrival (DoA)**: Using TDoA (Time Difference of Arrival) beamforming across 4 microphones to calculate 3D coordinates and pinpoint the exact server rack emitting the covert channel.
2. **Automated RF Jamming / Ultrasonic Masking**: Emitting localized white noise to physically scramble the air-gap channel once an exfiltration is detected.
