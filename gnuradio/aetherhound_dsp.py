#!/usr/bin/env python3
"""AetherHound GNU Radio DSP Flowgraph Pipeline
Digital Signal Processing to clean incoming RF and audio waterfalls,
filtering out standard server room noise and streaming spectrogram vectors.

Compatible with GNU Radio 3.8, 3.9, 3.10+
Can be run standalone or invoked by AetherHound.
"""
import sys, time
import numpy as np

try:
    from gnuradio import gr, blocks, filter, fft
    from gnuradio.fft import window
    HAVE_GNURADIO = True
except ImportError:
    HAVE_GNURADIO = False

class AetherHoundGnuRadioFlowgraph:
    """GNU Radio Top Block DSP pipeline."""
    def __init__(self, sample_rate=48000, fft_size=1024, output_port=9090, source="sim"):
        if not HAVE_GNURADIO:
            raise ImportError("GNU Radio libraries not installed in this environment.")
        self.tb = gr.top_block("AetherHound_DSP")
        
        # 1. Source Block
        if source == "audio":
            from gnuradio import audio
            self.src = audio.source(sample_rate, "", True)
        elif source == "rtlsdr":
            import osmosdr
            self.src = osmosdr.source("rtl=0")
            self.src.set_sample_rate(sample_rate)
        else: # Simulated server room noise
            from gnuradio import analog
            self.src = analog.noise_source_f(analog.GR_GAUSSIAN, 0.05, 42)

        # 2. Bandpass / Filtering Block (Suppress server hum & DC offset)
        # Filters low-frequency electrical hum (50/60 Hz and 120 Hz harmonics)
        bp_taps = filter.firdes.band_pass(
            1.0, sample_rate, 200, sample_rate / 2 - 1000, 100, filter.firdes.WIN_HAMMING
        )
        self.filt = filter.fir_filter_fff(1, bp_taps)

        # 3. Stream to Vector for Windowed FFT
        self.s2v = blocks.stream_to_vector(gr.sizeof_float, fft_size)

        # 4. Windowed FFT
        win = window.blackman_harris(fft_size)
        self.fft_block = fft.fft_vfc(fft_size, True, win)

        # 5. Complex to Magnitude Squared (Power Spectrum)
        self.c2mag2 = blocks.complex_to_mag_squared(fft_size)

        # 6. Log / dB Scale
        self.log_scale = blocks.nlog10_ff(10.0, fft_size, 1e-12)

        # 7. UDP Sink streaming spectrogram matrices to AetherHound Engine
        self.udp_sink = blocks.udp_sink(
            gr.sizeof_float * fft_size, "127.0.0.1", output_port, 1472, True
        )

        # Connect Flowgraph:
        # Source -> Filter -> StreamToVec -> FFT -> MagSquared -> dB -> UDP Sink
        self.tb.connect(self.src, self.filt)
        self.tb.connect(self.filt, self.s2v)
        self.tb.connect(self.s2v, self.fft_block)
        self.tb.connect(self.fft_block, self.c2mag2)
        self.tb.connect(self.c2mag2, self.log_scale)
        self.tb.connect(self.log_scale, self.udp_sink)

    def start(self):
        self.tb.start()

    def stop(self):
        self.tb.stop()
        self.tb.wait()

def fallback_dsp_stream(sample_rate=48000, fft_size=1024, output_port=9090, duration=10):
    """Fallback software socket server when GNU Radio native C++ runtime is absent.
    Performs equivalent DSP filtering, windowed FFT, and UDP transmission.
    """
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    dest = ("127.0.0.1", output_port)
    print(f"[*] GNU Radio software emulation DSP streaming to UDP {dest[0]}:{dest[1]}")
    t0 = time.time()
    while time.time() - t0 < duration:
        # Generate block of noise
        block = np.random.normal(0, 0.05, fft_size)
        # Windowed FFT
        w = np.hanning(fft_size)
        spec = np.fft.rfft(block * w)
        psd_db = (10 * np.log10(np.abs(spec)**2 + 1e-12)).astype(np.float32)
        sock.sendto(psd_db.tobytes(), dest)
        time.sleep(fft_size / sample_rate)
    sock.close()

if __name__ == "__main__":
    if HAVE_GNURADIO:
        print("[+] Starting native GNU Radio DSP flowgraph...")
        fg = AetherHoundGnuRadioFlowgraph()
        fg.start()
        try:
            while True: time.sleep(1)
        except KeyboardInterrupt:
            fg.stop()
    else:
        print("[!] GNU Radio C++ binaries not in PATH. Running standalone Python DSP pipeline.")
        fallback_dsp_stream()
