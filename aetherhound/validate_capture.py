"""Mid-Project Review Deliverable: Capture Validation Suite
Proves that AetherHound isolates the specific frequency spike caused by the mock CPU fan malware.
"""
import argparse, json, sys, time
import numpy as np
from . import config as C, dsp, morse
from .sources import SimSource
from .detector import Detector
from .mock_malware import acoustic_fan_synthesizer

def run_capture_validation(carrier_hz=18000.0, message="FAN 007", verbose=True):
    if verbose:
        print("=" * 70)
        print(" AETHERHOUND MID-PROJECT REVIEW: CAPTURE & SPIKE ISOLATION VALIDATION")
        print("=" * 70)
        print(f"[*] Target Mock Malware Carrier: {carrier_hz:.1f} Hz")
        print(f"[*] Injected Covert Payload: '{message}'")
    
    cfg = C.load()
    cfg["model"] = "auto"
    fs = cfg["fs"]
    frame = cfg["frame"]
    nbins = cfg["nbins"]
    fps = fs / frame
    
    # 1. Baseline training phase (normal server room noise)
    if verbose:
        print("[1] Collecting baseline server room hum (fan + power supply + thermal noise)...")
    baseline_src = SimSource(fs=fs, frame=frame, realtime=False, seed=42)
    X_train = [dsp.features(baseline_src.read(), frame, nbins) for _ in range(int(15 * fps))]
    baseline_src.close()
    
    freqs = dsp.bin_freqs(fs, 0, frame, nbins)
    det = Detector(cfg, freqs, fps)
    train_info = det.fit(np.array(X_train))
    if verbose:
        print(f"[+] Baseline Model: {train_info['kind'].upper()} | Calibrated Thr: {train_info['thr']:.2f}")

    # 2. Inject Mock Malware Covert Channel
    if verbose:
        print(f"[2] Injecting mock malware transmission at {carrier_hz:.1f} Hz ...")
    test_src = SimSource(fs=fs, frame=frame, realtime=False, inject_after=2.0,
                         message=message, carrier=carrier_hz, unit=0.12, amp=0.02, seed=99)
    
    detected_events = []
    spike_bins = []
    spike_freqs = []
    max_scores = []
    
    total_frames = int(14 * fps)
    for frame_idx in range(total_frames):
        ts = frame_idx / fps
        feat = dsp.features(test_src.read(), frame, nbins)
        res = det.process(feat, ts)
        if res["active"]:
            spike_bins.append(res["bin"])
            spike_freqs.append(res["freq"])
            max_scores.append(res["score"])
        if res["event"]:
            detected_events.append(res["event"])
            
    test_src.close()
    
    # 3. Validation Assessment
    expected_bin = int(np.argmin(np.abs(freqs - carrier_hz)))
    isolated_bin = int(np.median(spike_bins)) if spike_bins else -1
    isolated_freq = freqs[isolated_bin] if isolated_bin >= 0 else 0.0
    freq_error = abs(isolated_freq - carrier_hz)
    bin_width = (fs / 2.0) / nbins  # Width of each pooled frequency bin
    
    # Success if bin matches perfectly (within 1 bin width) and events decoded
    success = (len(detected_events) > 0) and (isolated_bin == expected_bin or freq_error <= bin_width)
    
    if verbose:
        print("\n" + "=" * 70)
        print(" CAPTURE VALIDATION TEST REPORT")
        print("=" * 70)
        print(f"  Target Injected Frequency : {carrier_hz:.1f} Hz (Bin {expected_bin})")
        print(f"  Isolated Spike Frequency  : {isolated_freq:.1f} Hz (Bin {isolated_bin})")
        print(f"  Frequency Deviation       : {freq_error:.2f} Hz (Bin Resolution: ±{bin_width:.1f} Hz)")
        print(f"  Peak Anomaly Z-Score      : {max(max_scores) if max_scores else 0:.1f} (Thr: {det.thr:.1f})")
        print(f"  Total Anomalous Frames    : {len(spike_bins)}")
        print(f"  Events Captured           : {len(detected_events)}")
        if detected_events:
            ev = detected_events[0]
            print(f"  Decoded Morse String      : '{ev['morse']}'")
            print(f"  Decoded Exfiltrated Text  : '{ev['decoded_text']}'")
            print(f"  Target Text Match         : {ev['decoded_text'].strip() == message.strip()}")
        print("-" * 70)
        if success:
            print("  [PASS] Mid-Project Milestone Met: Malware Frequency Spike Successfully Isolated!")
        else:
            print("  [FAIL] Failed to isolate frequency spike or capture covert channel.")
        print("=" * 70 + "\n")
        
    return {
        "success": success,
        "target_freq": carrier_hz,
        "isolated_freq": isolated_freq,
        "freq_error": freq_error,
        "events": detected_events
    }

def main():
    parser = argparse.ArgumentParser(description="Mid-Project Review: Capture Validation Test")
    parser.add_argument("--freq", type=float, default=18000.0, help="Carrier frequency to test")
    parser.add_argument("--message", default="FAN 007", help="Morse message to test")
    args = parser.parse_args()
    res = run_capture_validation(args.freq, args.message)
    sys.exit(0 if res["success"] else 1)

if __name__ == "__main__":
    main()
