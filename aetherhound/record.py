"""Record raw spectrum (RF I/Q) and acoustic (audio) data for baseline calibration and attack captures.
Supports RTL-SDR, HackRF, PyAudio/SoundDevice microphones, and simulation.
"""
import argparse, json, os, sys, time, wave
import numpy as np
from .sources import make_source
from . import config as C

def record_data(source_type, duration, output_path, cfg=None):
    if cfg is None:
        cfg = C.load()
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    
    print(f"[*] Initializing recording from source: {source_type} ...")
    src = make_source(source_type, cfg, realtime=True)
    fps = src.fs / src.block
    total_frames = int(duration * fps)
    
    print(f"[*] Source fs={src.fs} Hz, block={src.block}, is_complex={src.is_complex}")
    print(f"[*] Recording {duration:.1f}s ({total_frames} blocks) -> {output_path}")
    
    metadata = {
        "timestamp": time.time(),
        "datetime": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source": source_type,
        "sample_rate_hz": src.fs,
        "center_hz": getattr(src, "center", 0.0),
        "is_complex": src.is_complex,
        "duration_s": duration,
        "block_size": src.block,
        "channels": 1
    }
    
    samples_list = []
    t0 = time.time()
    try:
        for i in range(total_frames):
            blk = src.read()
            samples_list.append(blk)
            if i % max(1, int(fps * 2)) == 0 and i > 0:
                elapsed = time.time() - t0
                pct = (i / total_frames) * 100
                sys.stdout.write(f"\r    Progress: {i}/{total_frames} blocks ({pct:.1f}%) | {elapsed:.1f}s")
                sys.stdout.flush()
    except (KeyboardInterrupt, EOFError):
        print("\n[!] Recording interrupted.")
    finally:
        src.close()
    
    print("\n[*] Processing and writing output ...")
    data = np.concatenate(samples_list)
    metadata["total_samples"] = len(data)
    
    meta_path = output_path + ".meta.json"
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)
        
    if output_path.lower().endswith(".wav"):
        if src.is_complex:
            # Complex SDR data saved as 2-channel I/Q wav
            i_ch = np.real(data)
            q_ch = np.imag(data)
            stereo = np.column_stack((i_ch, q_ch))
            with wave.open(output_path, "wb") as w:
                w.setnchannels(2)
                w.setsampwidth(2)
                w.setframerate(int(src.fs))
                int16_data = (np.clip(stereo, -1.0, 1.0) * 32767).astype(np.int16)
                w.writeframes(int16_data.tobytes())
        else:
            with wave.open(output_path, "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(int(src.fs))
                int16_data = (np.clip(data, -1.0, 1.0) * 32767).astype(np.int16)
                w.writeframes(int16_data.tobytes())
    elif output_path.lower().endswith(".npy"):
        np.save(output_path, data)
    else:  # Raw binary file (complex64 or float32)
        dtype = np.complex64 if src.is_complex else np.float32
        data.astype(dtype).tofile(output_path)
        
    print(f"[+] Recording saved: {output_path} ({len(data)} samples)")
    print(f"[+] Metadata written: {meta_path}")
    return output_path

def main():
    parser = argparse.ArgumentParser(description="Record raw RF spectrum or acoustic covert channel data.")
    parser.add_argument("--source", default="audio", choices=["audio", "rtlsdr", "hackrf", "sim"],
                        help="Data source: audio (pyaudio/sounddevice mic), rtlsdr, hackrf, or sim")
    parser.add_argument("--duration", "-d", type=float, default=10.0, help="Duration to record in seconds")
    parser.add_argument("--out", "-o", required=True, help="Destination file (.wav, .npy, or .raw)")
    parser.add_argument("--config", "-c", help="Path to config.json")
    args = parser.parse_args()
    
    cfg = C.load(args.config)
    record_data(args.source, args.duration, args.out, cfg)

if __name__ == "__main__":
    main()
