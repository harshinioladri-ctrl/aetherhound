import argparse, glob, json, os, sys, time
import numpy as np
from . import config as C, dsp
from .sources import make_source
from .detector import Detector
from .engine import Engine, make_detector_geometry

def _common(p):
    p.add_argument("--config", help="Path to custom config.json")
    p.add_argument("--source", default="sim",
                   help="sim | audio | rtlsdr | hackrf | gnuradio:<url> | wav:<file>")

def cmd_train(a):
    cfg = C.load(a.config)
    if a.model: cfg["model"] = a.model
    src = make_source(a.source, cfg, realtime=(a.source not in ("sim",) and not a.source.startswith("wav:")))
    freqs, fps = make_detector_geometry(src, cfg)
    n = int((a.seconds or cfg["train_seconds"]) * fps); X = []
    print(f"[train] source={a.source} collecting ~{n} frames ({n/fps:.0f}s of 'normal') ...")
    try:
        for i in range(n):
            X.append(dsp.features(src.read(), cfg["frame"], cfg["nbins"], src.is_complex))
            if i % max(1, int(fps * 5)) == 0 and i: print(f"  {i}/{n}")
    except EOFError: pass
    finally: src.close()
    det = Detector(cfg, freqs, fps)
    info = det.fit(np.array(X))
    det.save(cfg["model_dir"])
    print("[train] done:", json.dumps({k: (round(v, 2) if isinstance(v, float) else v) for k, v in info.items()}))
    print(f"[train] saved to {cfg['model_dir']}/")

def cmd_run(a):
    cfg = C.load(a.config)
    src = make_source(a.source, cfg, realtime=not a.fast, inject_after=a.inject, message=a.message)
    freqs, fps = make_detector_geometry(src, cfg)
    det = Detector.load(cfg, cfg["model_dir"], freqs, fps)
    eng = Engine(cfg, src, det)
    try:
        if a.no_ui:
            end = time.time() + a.duration if a.duration else None; n = 0
            print(f"[run] headless, thr={det.thr:.1f}. Ctrl-C to stop.")
            try:
                while end is None or time.time() < end:
                    r = eng.step(); n += 1
                    if r["started"]: print(f"[ALERT] anomalous emission near {r['freq']:.0f} Hz")
                    if r["event"]:
                        e = eng.events[-1]
                        print(f"[EVENT] {e['time']} {e['freq_hz']:.0f}Hz {e['duration_s']}s decoded='{e['decoded_text']}' bits={e['bits'][:40]}")
            except (EOFError, KeyboardInterrupt): pass
            ev = eng.flush()
            if ev:
                e = eng.events[-1]
                print(f"[EVENT] {e['time']} {e['freq_hz']:.0f}Hz {e['duration_s']}s decoded='{e['decoded_text']}' (flushed at end of input)")
            print(f"[run] {n} frames, {len(eng.events)} event(s)")
        else:
            from . import ui
            ui_mode = getattr(a, "ui", "curses")
            ui.run(eng, cfg["log_dir"], mode=ui_mode)
            eng.flush()
    finally: src.close()

def cmd_demo(a):
    a.source = "sim"; a.seconds = 20; a.model = None; cmd_train(a)
    a.fast = False; a.no_ui = a.no_ui; a.duration = a.duration; a.inject = 8; a.message = "SECRET"; cmd_run(a)

def cmd_report(a):
    from . import report
    cfg = C.load(a.config)
    p = a.file or os.path.join(cfg["log_dir"], "events.jsonl")
    report.generate_report(p, html_output=a.html)

def cmd_record(a):
    from .record import record_data
    cfg = C.load(a.config)
    record_data(a.source, a.duration, a.out, cfg)

def cmd_malware(a):
    from .mock_malware import pulse_cpu_morse, direct_fan_sysfs_pulse, acoustic_fan_synthesizer
    if a.mode == "cpu":
        pulse_cpu_morse(a.message, a.unit, a.repeat)
    elif a.mode == "fan":
        direct_fan_sysfs_pulse(a.message, a.unit)
    elif a.mode in ("audio", "wav"):
        audio, fs = acoustic_fan_synthesizer(a.message, a.unit)
        if a.mode == "wav":
            import wave
            with wave.open(a.out, "wb") as w:
                w.setnchannels(1); w.setsampwidth(2); w.setframerate(fs)
                w.writeframes((np.clip(audio, -1, 1) * 32767).astype(np.int16).tobytes())
            print(f"[+] Written mock fan malware WAV to: {a.out}")
        else:
            import sounddevice as sd
            sd.play(audio.astype(np.float32), fs); sd.wait()

def cmd_validate(a):
    from .validate_capture import run_capture_validation
    res = run_capture_validation(a.freq, a.message)
    sys.exit(0 if res["success"] else 1)

def cmd_benchmark(a):
    from .benchmark import run_benchmark
    res = run_benchmark(a.frames, a.target_fps)
    sys.exit(0 if res["success"] else 1)

def cmd_dataset(a):
    from .dataset import generate_baseline_dataset
    generate_baseline_dataset(a.hours, out_path=a.out)

def main(argv=None):
    p = argparse.ArgumentParser("aetherhound", description="AetherHound: Air-Gapped RF & Acoustic Covert Channel Detector")
    sp = p.add_subparsers(dest="cmd", required=True)
    
    # train
    t = sp.add_parser("train", help="Train anomaly autoencoder on baseline server room hum")
    _common(t); t.add_argument("--seconds", type=float); t.add_argument("--model", choices=["auto", "ae", "stat"]); t.set_defaults(f=cmd_train)
    
    # run
    r = sp.add_parser("run", help="Run live real-time covert channel detection")
    _common(r); r.add_argument("--no-ui", action="store_true"); r.add_argument("--ui", choices=["curses", "ansi"], default="curses")
    r.add_argument("--duration", type=float); r.add_argument("--fast", action="store_true")
    r.add_argument("--inject", type=float, help="(sim) inject covert message after N sec")
    r.add_argument("--message", default="SECRET"); r.set_defaults(f=cmd_run)
    
    # demo
    d = sp.add_parser("demo", help="End-to-end simulated demonstration (train + inject + detect + decode)")
    _common(d); d.add_argument("--no-ui", action="store_true"); d.add_argument("--duration", type=float); d.set_defaults(f=cmd_demo)
    
    # report
    rp = sp.add_parser("report", help="Generate forensic report of detected covert transmissions")
    rp.add_argument("--config"); rp.add_argument("file", nargs="?"); rp.add_argument("--html", help="Path to export HTML dashboard"); rp.set_defaults(f=cmd_report)
    
    # record
    rc = sp.add_parser("record", help="Record raw RF spectrum or acoustic microphone stream")
    _common(rc); rc.add_argument("--duration", "-d", type=float, default=10.0); rc.add_argument("--out", "-o", required=True); rc.set_defaults(f=cmd_record)
    
    # malware
    m = sp.add_parser("malware", help="Benign mock malware (Fansmitter CPU fan modulation / AirHopper tone generator)")
    m.add_argument("--message", "-m", default="SECRET 007"); m.add_argument("--mode", choices=["cpu", "fan", "audio", "wav"], default="cpu")
    m.add_argument("--unit", "-u", type=float, default=0.2); m.add_argument("--repeat", "-r", type=int, default=1)
    m.add_argument("--out", default="mock_malware.wav"); m.set_defaults(f=cmd_malware)
    
    # validate
    v = sp.add_parser("validate", help="Mid-Project Review: Validate frequency spike capture from mock fan malware")
    v.add_argument("--freq", type=float, default=18000.0); v.add_argument("--message", default="FAN 007"); v.set_defaults(f=cmd_validate)
    
    # benchmark
    b = sp.add_parser("benchmark", help="Mid-Project Review: Benchmark UI & DSP for 30+ FPS requirement")
    b.add_argument("--frames", "-n", type=int, default=1000); b.add_argument("--target-fps", type=float, default=30.0); b.set_defaults(f=cmd_benchmark)
    
    # dataset
    ds = sp.add_parser("dataset", help="Generate multi-server hum baseline dataset")
    ds.add_argument("--hours", type=float, default=0.05); ds.add_argument("--out", default="data/baseline_server_hum.npz"); ds.set_defaults(f=cmd_dataset)
    
    a = p.parse_args(argv); a.f(a)
