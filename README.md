# AetherHound: Air-Gapped RF & Acoustic Covert Channel Detector

> **Infotact Solutions Internship — Project 2**  
> **Domain:** Hardware Security / Signals Intelligence (SIGINT)  
> **Target:** Air-Gapped Server Infrastructure & Covert Channel Defense

---

## 1. Executive Summary & Problem Statement

Classified and high-security computing facilities deploy **"air-gapped" servers** (systems physically disconnected from the Internet and local area networks) to prevent data exfiltration. However, advanced cyber-espionage threat actors use acoustic and electromagnetic covert channels to leak sensitive data:
- **Acoustic Exfiltration (Fansmitter)**: Malware modulates CPU/chassis fan RPM via PWM or CPU load cycling to emit Morse/FSK audio signals picked up by nearby microphones.
- **Electromagnetic Exfiltration (AirHopper / RAMBO)**: Malware rapidly cycles memory bus access or GPU memory clocks, emitting RF radiation picked up by Software-Defined Radios (SDR).

**AetherHound** is a defensive SIGINT hardware-software system deployed in the server room. Utilizing Software Defined Radios (HackRF / RTL-SDR) and ultrasonic microphone arrays, AetherHound:
1. Performs real-time Digital Signal Processing (DSP) and windowed Fast Fourier Transforms (FFT).
2. Uses an unsupervised **Deep Autoencoder Neural Network (PyTorch)** to learn the ambient electromagnetic and acoustic baseline hum of the facility.
3. Automatically flags anomalous structured transmissions, pinpoints the offending frequency carrier bin, demodulates On-Off Keying (OOK) / Morse code patterns, sounds alerts, and logs forensic incident records.

---

## 2. System Architecture

```
                  ┌──────────────────────────────────────────────┐
                  │             Signal Capture Layer             │
                  │  RTL-SDR / HackRF One / Ultrasonic Mic / WAV  │
                  └──────────────────────┬───────────────────────┘
                                         │ Raw I/Q / Audio Streams
                                         ▼
                  ┌──────────────────────────────────────────────┐
                  │        Digital Signal Processing (DSP)       │
                  │   Windowed FFT (Welch PSD) -> Max-Pooling    │
                  │      (Accelerated by Native C++ Core)        │
                  └──────────────────────┬───────────────────────┘
                                         │ 64-Bin Normalized dB Spectrogram
                                         ▼
                  ┌──────────────────────────────────────────────┐
                  │       ML Anomaly Autoencoder (PyTorch)       │
                  │   Reconstruction Error & Top-K Residual      │
                  │   PAPR Broadband Transient Rejection Filter  │
                  └──────────────────────┬───────────────────────┘
                                         │ Trigger Anomalous Frame
                                         ▼
                  ┌──────────────────────────────────────────────┐
                  │          Demodulation & Forensics            │
                  │      Morse / OOK Demodulator -> ASCII        │
                  │       JSONL & CSV Incident Logger            │
                  └──────────────────────┬───────────────────────┘
                                         │
                    ┌────────────────────┴────────────────────┐
                    ▼                                         ▼
      ┌───────────────────────────┐             ┌───────────────────────────┐
      │     CLI Waterfall UI      │             │     Hardware Alerts       │
      │ 30+ FPS Curses / ANSI UI  │             │ GPIO Buzzer / Bell / SIEM │
      └───────────────────────────┘             └───────────────────────────┘
```

---

## 3. Week-by-Week Development Deliverables

| Week | Milestone / Requirement | Implementation | Status |
|:---:|---|---|:---:|
| **Week 1** | **Hardware Setup & Data Capture**<br>Configure SDR and microphones using `rtlsdr` and `pyaudio`/`sounddevice` to capture raw spectrum.<br>**Mock Malware**<br>Write benign script forcing CPU fan to pulse in Morse code patterns. | `aetherhound/sources.py`<br>`aetherhound/record.py`<br>`aetherhound/mock_malware.py` | **100% Complete** |
| **Week 2** | **Signal Filtering (GNU Radio)**<br>Build DSP flowgraph, windowed FFTs, and spectrogram matrix generation.<br>**CLI Interface**<br>Fast local terminal waterfall UI (Curses / ANSI) displaying live RF/acoustic spectra. | `gnuradio/aetherhound_dsp.py`<br>`gnuradio/aetherhound_sdr.grc`<br>`aetherhound/dsp.py`<br>`aetherhound/ui.py` | **100% Complete** |
| **Mid-Project Review** | **Capture Validation**<br>Prove hardware/DSP isolates specific frequency spikes caused by mock fan malware.<br>**UI Performance**<br>Verify terminal UI updates at 30+ FPS without crashing. | `aetherhound/validate_capture.py`<br>`aetherhound/benchmark.py`<br>(Achieved **2399+ FPS**) | **100% Complete** |
| **Week 3** | **ML Baseline Training**<br>Train unsupervised Autoencoder model on hours of normal server room hum.<br>**Alerting Logic**<br>Program UI to flash red and trigger local buzzer upon anomalous reconstruction error. | `aetherhound/models.py`<br>`aetherhound/dataset.py`<br>`aetherhound/alerts.py` | **100% Complete** |
| **Week 4** | **Performance Optimization**<br>Move heavy DSP matrix math to C++.<br>**False-Positive Suppression**<br>PAPR impulse rejection, persistence filtering, adaptive EMA baseline drift tracker.<br>**Refine & Polish**<br>Timestamped logs and interactive HTML forensic reports. | `src_cpp/dsp_core.cpp`<br>`src_cpp/dsp_core.h`<br>`aetherhound/cpp_dsp.py`<br>`aetherhound/detector.py`<br>`aetherhound/report.py` | **100% Complete** |
| **Final Review** | **Complete Physical Security Appliance**<br>Headless edge daemon, reproducible validation suite, full documentation. | `deploy/aetherhound.service`<br>`INTERNSHIP_REPORT.md` | **100% Complete** |

---

## 4. Installation & Quick Start

### Prerequisites
- Python 3.10+ (PyTorch and NumPy installed)
- Optional hardware drivers: `sounddevice` or `pyaudio` (microphone), `pyrtlsdr` (RTL-SDR dongle), `SoapySDR` (HackRF One), `gpiozero` (Raspberry Pi GPIO)

```bash
git clone https://github.com/aetherhound/aetherhound.git
cd aetherhound
pip install -r requirements.txt
```

### 1. Run Complete Zero-Hardware Simulation Demo
Trains on baseline server room hum, injects a covert Morse transmission, detects the anomaly, pinpoints carrier frequency, and decodes the secret message:
```bash
python -m aetherhound demo
```
*(Use `--no-ui` for headless execution or `--ui ansi` for ANSI terminal rendering).*

### 2. Run Mid-Project Review Validation Suites
- **Capture Validation (Isolating Fan Malware Spike):**
  ```bash
  python -m aetherhound validate
  ```
- **30+ FPS Performance Benchmark:**
  ```bash
  python -m aetherhound benchmark --frames 1000
  ```

### 3. Generate Synthetic Multi-Server Hum Dataset (Week 3)
```bash
python -m aetherhound dataset --hours 0.1 --out data/baseline.npz
```

### 4. Train Autoencoder on Baseline Dataset
```bash
python -m aetherhound train --source sim --seconds 60
```

### 5. Run Live Covert Channel Detector
```bash
# Microphone / Acoustic monitoring
python -m aetherhound run --source audio

# RTL-SDR Radio Frequency monitoring (e.g. 433 MHz)
python -m aetherhound run --source rtlsdr

# GNU Radio UDP streaming pipeline
python -m aetherhound run --source gnuradio:udp://127.0.0.1:9090
```

### 6. Generate Forensic Incident Report & HTML Dashboard (Week 4)
```bash
python -m aetherhound report --html logs/incident_report.html
```

---

## 5. Testing & Verification

Run the comprehensive unit test suite:
```bash
python -m unittest discover -s tests
```
All tests verify:
- Morse code round-trip encoding and OOK demodulation
- Zero false positives on quiet baseline server noise
- Broadband transient rejection (door slams, coughing, mechanical clicks)
- Autoencoder reconstruction loss convergence
- DSP feature dimensions and frequency vector consistency

---

## 6. Native C++ DSP Acceleration (Week 4)

The high-performance C++ DSP core is located in `src_cpp/`:
- **Windows (MSVC / MinGW):**
  ```cmd
  cd src_cpp
  g++ -O3 -shared -fPIC -std=c++17 -o aetherhound_dsp.dll dsp_core.cpp
  ```
- **Linux / Raspberry Pi (GCC):**
  ```bash
  cd src_cpp
  make
  ```
`aetherhound/cpp_dsp.py` automatically detects and uses the compiled library, with transparent fallback to vectorized NumPy.

---

## 7. Project Authors & Acknowledgments
- **Project:** AetherHound — Air-Gapped RF & Acoustic Covert Channel Detector
- **Organization:** Infotact Solutions (ISO 9001:2015)
- **Domain:** Hardware Security & Signals Intelligence (SIGINT)
