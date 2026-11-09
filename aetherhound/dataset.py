"""Baseline Server Room Emission Dataset Generator & Loader.
Generates hours of synthetic or recorded multi-server electromagnetic and acoustic hum,
incorporating:
- Dual server rack cooling fans with aerodynamic blade-passing harmonics
- AC mains hum (50/60 Hz) and rectifier bridge harmonics (100/120 Hz)
- Server power supply unit (PSU) switching noise (~16-22 kHz)
- Random hard drive head actuator seek jitter
- HVAC ambient airflow rumble and thermal baseline drift
"""
import argparse, json, os, sys, time
import numpy as np
from . import dsp

class ServerRoomHumGenerator:
    """Generates realistic server room acoustic and RF baseline emissions."""
    def __init__(self, fs=48000, frame=1024, seed=42):
        self.fs = fs
        self.frame = frame
        self.rng = np.random.default_rng(seed)
        self.n = 0
        self.thermal_drift_phase = 0.0

    def generate_block(self):
        n = self.frame
        t = (self.n + np.arange(n)) / self.fs
        
        # 1. Thermal drift: slow modulation of fan speeds
        drift = 1.0 + 0.015 * np.sin(2 * np.pi * 0.02 * t)
        
        # 2. Server Cooling Fans (7-blade primary fan @ ~3000 RPM, 9-blade secondary fan @ ~2700 RPM)
        f_fan1 = 350.0 * drift    # Blade passing frequency
        f_fan2 = 405.0 * drift
        fan_sound = (
            0.025 * np.sin(2 * np.pi * f_fan1 * t) +
            0.015 * np.sin(4 * np.pi * f_fan1 * t) +
            0.010 * np.sin(6 * np.pi * f_fan1 * t) +
            0.020 * np.sin(2 * np.pi * f_fan2 * t) +
            0.012 * np.sin(4 * np.pi * f_fan2 * t)
        )
        
        # 3. Electrical mains hum (60 Hz + 120/180/240 Hz harmonics)
        mains_sound = np.zeros(n)
        for harmonic in [1, 2, 3, 4]:
            mains_sound += (0.012 / harmonic) * np.sin(2 * np.pi * 60 * harmonic * t)
            
        # 4. Server PSU switching frequency hum (near ultrasonic: 19.2 kHz)
        psu_whine = 0.006 * np.sin(2 * np.pi * 19200 * t)
        
        # 5. Airflow turbulence pink-like noise
        white_noise = self.rng.normal(0, 0.015, n)
        
        # 6. Random disk seek / mechanical clicks (sparse Poisson transients)
        disk_clicks = np.zeros(n)
        if self.rng.random() < 0.08:
            click_pos = self.rng.integers(0, n - 20)
            decay = np.exp(-np.linspace(0, 5, 20))
            disk_clicks[click_pos:click_pos + 20] = 0.04 * decay * self.rng.choice([-1, 1])
            
        combined = fan_sound + mains_sound + psu_whine + white_noise + disk_clicks
        self.n += n
        return combined

def generate_baseline_dataset(hours=1.0, fs=48000, frame=1024, nbins=64, out_path="data/baseline_server_hum.npz"):
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    fps = fs / frame
    total_frames = int(hours * 3600 * fps)
    
    print(f"[*] Generating {hours:.2f} hour(s) of baseline server room emissions ({total_frames} frames)...")
    gen = ServerRoomHumGenerator(fs=fs, frame=frame)
    features_list = []
    
    t0 = time.time()
    for i in range(total_frames):
        raw = gen.generate_block()
        feat = dsp.features(raw, frame, nbins)
        features_list.append(feat)
        if i % max(1, int(fps * 30)) == 0 and i > 0:
            elapsed = time.time() - t0
            pct = (i / total_frames) * 100
            sys.stdout.write(f"\r    Processed: {i}/{total_frames} frames ({pct:.1f}%) | {elapsed:.1f}s")
            sys.stdout.flush()
            
    print(f"\n[*] Saving dataset to {out_path} ...")
    X = np.array(features_list, dtype=np.float32)
    freqs = dsp.bin_freqs(fs, 0, frame, nbins)
    np.savez_compressed(out_path, X=X, freqs=freqs, fs=fs, frame=frame, nbins=nbins, hours=hours)
    print(f"[+] Dataset successfully created: {out_path} (Shape: {X.shape}, Size: {os.path.getsize(out_path)/1024/1024:.2f} MB)")
    return out_path

def main():
    parser = argparse.ArgumentParser(description="Generate synthetic multi-server hum baseline dataset for ML Autoencoder training.")
    parser.add_argument("--hours", type=float, default=0.05, help="Duration of training data in hours (e.g. 0.05 = 3 mins, 1.0 = 1 hour)")
    parser.add_argument("--out", default="data/baseline_server_hum.npz", help="Output file (.npz)")
    args = parser.parse_args()
    generate_baseline_dataset(args.hours, out_path=args.out)

if __name__ == "__main__":
    main()
