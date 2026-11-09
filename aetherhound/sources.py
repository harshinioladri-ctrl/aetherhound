"""Signal sources: sim (no hardware), wav replay, microphone, RTL-SDR, HackRF."""
import time, wave
import numpy as np
from .morse import encode_envelope

class _Base:
    is_complex = False
    center = 0.0
    def close(self): pass

class SimSource(_Base):
    """Synthetic server room: fan whine + hum + noise. Optionally injects a keyed
    covert tone (ultrasonic carrier) after `inject_after` seconds."""
    def __init__(self, fs=48000, frame=1024, realtime=False, inject_after=None,
                 message="SECRET", carrier=18000.0, unit=0.12, amp=0.015, seed=1):
        self.fs, self.block, self.realtime = fs, frame, realtime
        self.rng = np.random.default_rng(seed); self.n = 0
        self.carrier, self.amp = carrier, amp
        self.env, self.start = None, None
        if inject_after is not None:
            self.env = encode_envelope(message, int(unit * fs))
            self.start = int(inject_after * fs)
        self._t0 = time.monotonic()
    def read(self):
        n = self.block; t = (self.n + np.arange(n)) / self.fs
        x = self.rng.normal(0, 0.01, n)
        for k in range(1, 6): x += (0.02 / k) * np.sin(2 * np.pi * 120 * k * t)
        x += 0.01 * np.sin(2 * np.pi * 2400 * t)
        if self.env is not None:
            a, b = self.n - self.start, self.n - self.start + n
            if b > 0 and a < len(self.env):
                seg = np.zeros(n, bool); lo, hi = max(a, 0), min(b, len(self.env))
                seg[lo - a:hi - a] = self.env[lo:hi]
                x += self.amp * seg * np.sin(2 * np.pi * self.carrier * t)
        self.n += n
        if self.realtime:
            d = self._t0 + self.n / self.fs - time.monotonic()
            if d > 0: time.sleep(d)
        return x

class WavSource(_Base):
    def __init__(self, path, frame=1024, realtime=False):
        self.w = wave.open(path, "rb"); self.fs = self.w.getframerate()
        self.ch = self.w.getnchannels(); self.block = frame; self.realtime = realtime
        if self.w.getsampwidth() != 2: raise ValueError("WAV must be 16-bit PCM")
    def read(self):
        raw = self.w.readframes(self.block)
        if len(raw) < self.block * self.ch * 2: raise EOFError
        x = np.frombuffer(raw, np.int16).reshape(-1, self.ch)[:, 0] / 32768.0
        if self.realtime: time.sleep(self.block / self.fs)
        return x
    def close(self): self.w.close()

class AudioSource(_Base):
    """Microphone: supports both sounddevice and pyaudio with auto-fallback."""
    def __init__(self, fs=48000, frame=1024, device=None):
        self.fs, self.block = fs, frame
        self._backend = None
        try:
            import sounddevice as sd
            self._backend = "sounddevice"
            self.s = sd.InputStream(samplerate=fs, channels=1, blocksize=frame, device=device)
            self.s.start()
        except ImportError:
            try:
                import pyaudio
                self._backend = "pyaudio"
                self.pa = pyaudio.PyAudio()
                self.stream = self.pa.open(format=pyaudio.paInt16, channels=1, rate=fs,
                                          input=True, frames_per_buffer=frame)
            except ImportError:
                raise ImportError("Microphone capture requires either 'sounddevice' or 'pyaudio' installed. "
                                  "Install with: pip install sounddevice  OR  pip install pyaudio")

    def read(self):
        if self._backend == "sounddevice":
            return self.s.read(self.block)[0][:, 0].astype(np.float64)
        elif self._backend == "pyaudio":
            raw = self.stream.read(self.block, exception_on_overflow=False)
            return np.frombuffer(raw, dtype=np.int16).astype(np.float64) / 32768.0

    def close(self):
        if self._backend == "sounddevice":
            try:
                self.s.stop(); self.s.close()
            except Exception: pass
        elif self._backend == "pyaudio":
            try:
                self.stream.stop_stream(); self.stream.close(); self.pa.terminate()
            except Exception: pass

class GnuRadioSource(_Base):
    """Network streaming source fed by GNU Radio UDP or TCP flowgraph."""
    def __init__(self, host="127.0.0.1", port=9090, frame=1024, proto="udp", is_complex=False, fs=48000):
        import socket
        self.fs = fs
        self.block = frame
        self.is_complex = is_complex
        self.proto = proto
        self.dtype = np.complex64 if is_complex else np.float32
        itemsize = np.dtype(self.dtype).itemsize
        self.bytes_needed = frame * itemsize
        if proto == "udp":
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.bind((host, port))
            self.sock.settimeout(3.0)
        else:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((host, port))
            self.sock.settimeout(3.0)

    def read(self):
        buf = bytearray()
        while len(buf) < self.bytes_needed:
            try:
                chunk = self.sock.recv(self.bytes_needed - len(buf))
                if not chunk: raise EOFError("GNU Radio stream disconnected")
                buf.extend(chunk)
            except Exception as e:
                raise EOFError(f"GNU Radio stream timeout: {e}")
        return np.frombuffer(buf, dtype=self.dtype)

    def close(self):
        try: self.sock.close()
        except Exception: pass

class SDRSource(_Base):
    is_complex = True
    def __init__(self, kind, fs=2.4e6, center=433e6, frame=1024, fps=40):
        self.fs, self.center, self.kind = fs, center, kind
        self.block = (int(fs // fps) // frame) * frame
        if kind == "rtlsdr":
            from rtlsdr import RtlSdr
            self.d = RtlSdr(); self.d.sample_rate = fs; self.d.center_freq = center; self.d.gain = "auto"
        else:  # hackrf via SoapySDR
            import SoapySDR
            from SoapySDR import SOAPY_SDR_RX, SOAPY_SDR_CF32
            self.d = SoapySDR.Device(dict(driver="hackrf"))
            self.d.setSampleRate(SOAPY_SDR_RX, 0, fs); self.d.setFrequency(SOAPY_SDR_RX, 0, center)
            self.st = self.d.setupStream(SOAPY_SDR_RX, SOAPY_SDR_CF32); self.d.activateStream(self.st)
    def read(self):
        if self.kind == "rtlsdr": return np.asarray(self.d.read_samples(self.block))
        buf = np.zeros(self.block, np.complex64); got = 0
        while got < self.block:
            r = self.d.readStream(self.st, [buf[got:]], self.block - got)
            if r.ret > 0: got += r.ret
        return buf
    def close(self):
        try:
            if self.kind == "rtlsdr": self.d.close()
            else: self.d.deactivateStream(self.st); self.d.closeStream(self.st)
        except Exception: pass

def make_source(spec, cfg, realtime=True, inject_after=None, message="SECRET"):
    f = cfg["frame"]
    if spec == "sim": return SimSource(cfg["fs"], f, realtime, inject_after, message)
    if spec.startswith("wav:"): return WavSource(spec[4:], f, realtime)
    if spec == "audio": return AudioSource(cfg["fs"], f)
    if spec.startswith("gnuradio:"):
        # Format gnuradio:udp://127.0.0.1:9090 or gnuradio:tcp://127.0.0.1:9090
        url = spec[9:]
        proto = "udp" if url.startswith("udp://") else "tcp"
        addr = url.split("://")[-1]
        host, port = addr.split(":")
        return GnuRadioSource(host, int(port), frame=f, proto=proto,
                              is_complex=cfg.get("is_complex", False), fs=cfg["fs"])
    if spec in ("rtlsdr", "hackrf"): return SDRSource(spec, center=cfg["center_hz"] or 433e6, frame=f)
    raise ValueError("unknown source: " + spec)
