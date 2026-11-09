import json
DEFAULTS = dict(
    fs=48000, center_hz=0, frame=1024, nbins=64,
    train_seconds=45, model="auto",      # auto | ae | stat
    topk=3, thr_margin=1.3, persist=4, release_sec=1.0,
    ema_alpha=0.0005,                    # slow baseline drift adaptation
    ignore_bands=[],                     # [[lo_hz, hi_hz], ...] known-noisy bands
    log_dir="logs", model_dir="models",
    buzzer_gpio=None, bell=True,
)
def load(path=None):
    cfg = dict(DEFAULTS)
    if path:
        with open(path) as f:
            cfg.update(json.load(f))
    return cfg
