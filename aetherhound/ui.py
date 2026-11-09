"""Hacker-style curses terminal UI: live RF/acoustic waterfall + alert panel."""
import curses, time, os
from collections import deque
import numpy as np
SHADE = " .:-=+*#%@"

def fmt_hz(f):
    a = abs(f)
    return f"{f/1e6:.3f}MHz" if a >= 1e6 else (f"{f/1e3:.2f}kHz" if a >= 1e3 else f"{f:.0f}Hz")

def run(engine, snapshot_dir="logs", mode="curses"):
    if mode == "ansi":
        return run_ansi(engine, snapshot_dir)
    try:
        curses.wrapper(_main, engine, snapshot_dir)
    except Exception as e:
        # Graceful fallback if terminal environment doesn't support curses
        print(f"[!] Curses UI initialization failed ({e}). Falling back to ANSI live console UI...")
        run_ansi(engine, snapshot_dir)

def run_ansi(eng, snapdir="logs", target_fps=35):
    """High-speed ANSI terminal live waterfall for environments without curses."""
    import sys
    print("\033[2J\033[H", end="") # clear screen
    rows = deque(maxlen=24); freqs = eng.det.freqs; nb = len(freqs)
    lo = hi = None; fps_t = time.time(); fcount = 0; fps = 0.0; last = None
    frame_dur = 1.0 / target_fps
    
    print("[*] AetherHound ANSI Waterfall Live Display (Press Ctrl+C to stop)")
    try:
        while True:
            t0 = time.time()
            try: res = eng.step()
            except (EOFError, StopIteration): break
            if lo is None:
                lo = float(eng.det.mu.min()) - 6; hi = float(eng.det.mu.max()) + 25
            rows.append((res["feat"], res["active"]))
            if res["event"]: last = eng.events[-1]
            fcount += 1
            if time.time() - fps_t >= 1:
                fps = fcount / (time.time() - fps_t); fcount = 0; fps_t = time.time()
                
            w = 70
            alert = res["active"]
            status_color = "\033[91;1m" if alert else "\033[92m"
            reset_color = "\033[0m"
            
            out = ["\033[H"] # move cursor to top-left
            title = f"{status_color}=== AETHERHOUND // {'[ ALERT: COVERT CHANNEL DETECTED ]' if alert else '[ STATUS: NOMINAL ]'} ==={reset_color}\n"
            out.append(title)
            
            bar_w = 25
            ratio = min(1.0, res["score"] / (res["thr"] * 2))
            bar = "#" * int(ratio * bar_w) + "-" * (bar_w - int(ratio * bar_w))
            out.append(f"Score: {res['score']:7.1f} | Thr: {res['thr']:6.1f} | FPS: {fps:4.1f} [{bar}]\n")
            
            if alert:
                out.append(f"\033[91;1m>>> ANOMALOUS EMISSION PINPOINTED @ {fmt_hz(res['freq'])} <<<\033[0m\n")
            else:
                out.append(">>> Scanning RF & Acoustic Spectrum Waterfall ... <<<\n")
                
            out.append("-" * w + "\n")
            vis = list(rows)[-16:]
            for feat, act in vis:
                v = np.clip((feat - lo) / (hi - lo), 0, 0.999)
                line = ''.join(SHADE[int(v[min(nb - 1, int(x * nb / w))] * len(SHADE))] for x in range(w))
                c = "\033[91m" if act else "\033[36m"
                out.append(f"{c}{line}{reset_color}\n")
            out.append("-" * w + "\n")
            out.append(f"{fmt_hz(freqs[0])}".ljust(w // 2) + f"{fmt_hz(freqs[-1])}".rjust(w // 2) + "\n")
            if last:
                out.append(f"\033[93mLast Alert: {last['time'][11:19]} @ {fmt_hz(last['freq_hz'])} ({last['duration_s']}s) Decoded: '{last['decoded_text']}'\033[0m\n")
            
            sys.stdout.write("".join(out))
            sys.stdout.flush()
            
            # FPS pacing
            elapsed = time.time() - t0
            if elapsed < frame_dur:
                time.sleep(frame_dur - elapsed)
    except KeyboardInterrupt:
        pass
    print("\n[+] Dashboard stopped cleanly.")

def _main(scr, eng, snapdir):
    curses.curs_set(0); scr.nodelay(True)
    curses.start_color(); curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_GREEN, -1); curses.init_pair(2, curses.COLOR_RED, -1)
    curses.init_pair(3, curses.COLOR_CYAN, -1); curses.init_pair(4, curses.COLOR_YELLOW, -1)
    rows = deque(maxlen=200); freqs = eng.det.freqs; nb = len(freqs)
    lo = hi = None; fps_t = time.time(); fcount = 0; fps = 0.0; last = None
    while True:
        k = scr.getch()
        if k in (ord('q'), 27): break
        if k == ord('m'): eng.alert.muted = not eng.alert.muted
        if k == ord('r'): eng.det.reset(); rows.clear()
        if k == ord('s'):
            os.makedirs(snapdir, exist_ok=True)
            import numpy as _n; _n.savetxt(os.path.join(snapdir, f"snapshot_{int(time.time())}.csv"),
                                           _n.array([r[0] for r in rows]), delimiter=",", fmt="%.1f")
        try: res = eng.step()
        except EOFError: break
        if lo is None:
            lo = float(eng.det.mu.min()) - 6; hi = float(eng.det.mu.max()) + 25
        rows.append((res["feat"], res["active"]))
        if res["event"]: last = eng.events[-1]
        fcount += 1
        if time.time() - fps_t >= 1: fps = fcount / (time.time() - fps_t); fcount = 0; fps_t = time.time()
        h, w = scr.getmaxyx()
        if h < 12 or w < 40: continue
        scr.erase(); alert = res["active"]; col = curses.color_pair(2 if alert else 1) | curses.A_BOLD
        title = " AETHERHOUND // covert-channel detector "
        scr.addstr(0, 0, (title + "[ALERT]" if alert else title + "[ nominal ]")[:w - 1], col)
        bar_w = max(10, w - 34); ratio = min(1.0, res["score"] / (res["thr"] * 2))
        scr.addstr(1, 0, f"score {res['score']:8.1f} thr {res['thr']:7.1f} fps {fps:4.0f} ["[:w - 1], curses.color_pair(3))
        x0 = 36
        if x0 + bar_w + 1 < w:
            scr.addstr(1, x0, "#" * int(ratio * bar_w) + "-" * (bar_w - int(ratio * bar_w)) + "]", col)
        if alert:
            scr.addstr(2, 0, f">>> ANOMALOUS EMISSION @ {fmt_hz(res['freq'])}"[:w - 1], curses.color_pair(2) | curses.A_BOLD)
        top, bot = 3, h - 5; height = bot - top
        vis = list(rows)[-height:]
        for i, (feat, act) in enumerate(vis):
            y = top + height - len(vis) + i
            v = np.clip((feat - lo) / (hi - lo), 0, 0.999)
            line = ''.join(SHADE[int(v[min(nb - 1, int(x * nb / (w - 1)))] * len(SHADE))] for x in range(w - 1))
            scr.addstr(y, 0, line, curses.color_pair(2 if act else 1))
        scr.addstr(bot, 0, f"{fmt_hz(freqs[0])}".ljust(w // 2) + f"{fmt_hz(freqs[-1])}".rjust(w // 2 - 1), curses.color_pair(3))
        if alert:
            x = int(res["bin"] * (w - 1) / nb); scr.addstr(bot + 1, min(x, w - 2), "^", curses.color_pair(2) | curses.A_BOLD)
        if last:
            scr.addstr(bot + 2, 0, f"last: {last['time'][11:19]} {fmt_hz(last['freq_hz'])} {last['duration_s']}s decoded='{last['decoded_text']}'"[:w - 1], curses.color_pair(4))
        scr.addstr(h - 1, 0, f"[q]uit [m]ute{'(ON)' if eng.alert.muted else ''} [r]eset [s]napshot  events:{len(eng.events)}"[:w - 1], curses.color_pair(3))
        scr.refresh()
