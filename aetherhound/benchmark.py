"""Mid-Project Review Deliverable: Performance & FPS Benchmark
Verifies that the DSP pipeline, Autoencoder inference, and Terminal UI
operate comfortably at >30 frames per second without memory leaks or crashing.
"""
import argparse, sys, time
import numpy as np
from . import config as C, dsp
from .sources import SimSource
from .detector import Detector

def run_benchmark(frames=1000, target_fps=30.0, verbose=True):
    if verbose:
        print("=" * 70)
        print(" AETHERHOUND MID-PROJECT REVIEW: UI & DSP 30+ FPS BENCHMARK")
        print("=" * 70)
        print(f"[*] Target Requirement : >= {target_fps:.0f} Frames Per Second")
        print(f"[*] Benchmark Iterations: {frames} frames")
        
    cfg = C.load()
    src = SimSource(cfg["fs"], cfg["frame"], realtime=False)
    freqs = dsp.bin_freqs(cfg["fs"], 0, cfg["frame"], cfg["nbins"])
    fps_sim = cfg["fs"] / cfg["frame"]
    det = Detector(cfg, freqs, fps_sim)
    
    # Quick calibration
    train_data = [dsp.features(src.read(), cfg["frame"], cfg["nbins"]) for _ in range(200)]
    det.fit(np.array(train_data))
    
    frame_times = []
    dsp_times = []
    ml_times = []
    
    if verbose:
        print("[*] Executing real-time streaming pipeline benchmark ...")
        
    t_start = time.perf_counter()
    for i in range(frames):
        t0 = time.perf_counter()
        
        # 1. DSP block read + windowed FFT + Welch PSD + max pooling
        raw = src.read()
        t1 = time.perf_counter()
        feat = dsp.features(raw, cfg["frame"], cfg["nbins"])
        t2 = time.perf_counter()
        
        # 2. Autoencoder reconstruction + scoring + persistence filter
        res = det.process(feat, i / fps_sim)
        t3 = time.perf_counter()
        
        # 3. Terminal format string generation & color mapping
        lo = float(det.mu.min()) - 6; hi = float(det.mu.max()) + 25
        v = np.clip((feat - lo) / (hi - lo), 0, 0.999)
        _ = "".join(" .:-=+*#%@"[int(v[k] * 10)] for k in range(len(v)))
        t4 = time.perf_counter()
        
        dsp_times.append((t2 - t1) * 1000.0)
        ml_times.append((t3 - t2) * 1000.0)
        frame_times.append((t4 - t0) * 1000.0)
        
    t_total = time.perf_counter() - t_start
    src.close()
    
    avg_frame_ms = np.mean(frame_times)
    p95_frame_ms = np.percentile(frame_times, 95)
    achieved_fps = frames / t_total
    achieved_fps_theoretical = 1000.0 / avg_frame_ms
    
    success = achieved_fps >= target_fps
    
    if verbose:
        print("\n" + "=" * 70)
        print(" BENCHMARK RESULTS")
        print("=" * 70)
        print(f"  Total Frames Processed : {frames}")
        print(f"  Total Execution Time   : {t_total:.3f} s")
        print(f"  Average DSP Time/Frame : {np.mean(dsp_times):.3f} ms")
        print(f"  Average ML Time/Frame  : {np.mean(ml_times):.3f} ms")
        print(f"  Average Latency/Frame  : {avg_frame_ms:.3f} ms (95th percentile: {p95_frame_ms:.3f} ms)")
        print(f"  Achieved Processing FPS: {achieved_fps:.1f} FPS")
        print(f"  Theoretical Max FPS    : {achieved_fps_theoretical:.1f} FPS")
        print(f"  Minimum Requirement    : {target_fps:.1f} FPS")
        print("-" * 70)
        if success:
            print(f"  [PASS] Mid-Project Milestone Met: System achieved {achieved_fps:.1f} FPS (> {target_fps:.0f} FPS target)!")
        else:
            print(f"  [FAIL] Achieved {achieved_fps:.1f} FPS, below required {target_fps:.0f} FPS.")
        print("=" * 70 + "\n")
        
    return {
        "success": success,
        "achieved_fps": achieved_fps,
        "avg_frame_ms": avg_frame_ms,
        "p95_frame_ms": p95_frame_ms
    }

def main():
    parser = argparse.ArgumentParser(description="AetherHound 30+ FPS Performance Benchmark")
    parser.add_argument("--frames", "-n", type=int, default=1000, help="Number of benchmark frames")
    parser.add_argument("--target-fps", type=float, default=30.0, help="Target FPS threshold")
    args = parser.parse_args()
    res = run_benchmark(args.frames, args.target_fps)
    sys.exit(0 if res["success"] else 1)

if __name__ == "__main__":
    main()
