"""Baseline learning, anomaly scoring, persistence filter, event extraction + decoding."""
import os
from collections import deque
import numpy as np
from .models import make_model, StatModel, TorchAE
from . import morse

class Detector:
    def __init__(self, cfg, freqs, fps):
        self.cfg, self.freqs, self.fps = cfg, np.asarray(freqs), fps
        self.nbins = len(freqs)
        self.mask = np.ones(self.nbins)
        for lo, hi in cfg["ignore_bands"]:
            self.mask[(self.freqs >= lo) & (self.freqs <= hi)] = 0
        self.mu = self.var = self.thr = self.model = None
        self.reset()

    def reset(self):
        self.hist = deque(maxlen=int(self.fps * 30)); self.n = 0
        self.consec = self.quiet = 0; self.active = False; self.run_start = 0; self.peak = 0.0

    # ---------- training ----------
    def _score(self, r):
        k = self.cfg["topk"]
        return float(np.sort((r * self.mask) ** 2)[-k:].mean())

    def fit(self, X):
        X = np.asarray(X)
        self.mu = X.mean(0); self.var = np.maximum(X.var(0), 0.25)
        Z = (X - self.mu) / np.sqrt(self.var)
        self.model = make_model(self.cfg["model"], self.nbins); self.model.fit(Z)
        scores = np.array([self._score(self.model.residual(z)) for z in Z])
        self.thr = float(np.percentile(scores, 99.9) * self.cfg["thr_margin"])
        return dict(kind=self.model.kind, frames=len(X), thr=self.thr,
                    train_score_mean=float(scores.mean()))

    def save(self, d):
        os.makedirs(d, exist_ok=True)
        np.savez(os.path.join(d, "baseline.npz"), mu=self.mu, var=self.var, thr=self.thr,
                 kind=self.model.kind, freqs=self.freqs)
        self.model.save(os.path.join(d, "ae.pt"))

    @classmethod
    def load(cls, cfg, d, freqs, fps):
        z = np.load(os.path.join(d, "baseline.npz"), allow_pickle=False)
        if len(z["freqs"]) != len(freqs) or not np.allclose(z["freqs"], freqs):
            raise ValueError("Model was trained with a different source/sample-rate/bins. Re-run `train`.")
        det = cls(cfg, freqs, fps)
        det.mu, det.var, det.thr = z["mu"], z["var"], float(z["thr"])
        kind = str(z["kind"])
        det.model = StatModel() if kind == "stat" else TorchAE(det.nbins)
        det.model.load(os.path.join(d, "ae.pt"), det.nbins)
        return det

    # ---------- runtime ----------
    def _is_broadband_impulse(self, z):
        """Rejects false positives from wideband transient room noises (door slams,
        coughing, footsteps). A covert channel has high peak-to-average spectral ratio (PAPR)
        (concentrated in 1-2 bins), whereas room transients elevate power across all bins.
        """
        masked_z = np.maximum(0.0, z * self.mask)
        mean_z = masked_z.mean()
        if mean_z < 1.0:
            return False
        peak_z = masked_z.max()
        papr = peak_z / (mean_z + 1e-6)
        # Narrowband covert channel has PAPR >> 2.5 (often 10-60); wideband transient has PAPR near 1.0-1.8
        return papr < 2.5

    def process(self, feat, ts):
        z = (feat - self.mu) / np.sqrt(self.var)
        r = self.model.residual(z)
        score = self._score(r)
        self.hist.append(z * self.mask); self.n += 1
        
        # Check if score exceeds threshold AND is not a wideband transient room noise
        is_broadband = self._is_broadband_impulse(z)
        over = (score > self.thr) and not is_broadband
        event = started = False
        if over:
            if self.consec == 0: self.run_start = self.n - 1; self.run_ts = ts; self.peak = 0.0
            self.consec += 1; self.quiet = 0; self.peak = max(self.peak, score)
            if not self.active and self.consec >= self.cfg["persist"]:
                self.active = True; started = True
        else:
            if self.active:
                self.quiet += 1
                if self.quiet >= int(self.cfg["release_sec"] * self.fps):
                    event = self._finish(ts); self.active = False; self.consec = self.quiet = 0
            else:
                self.consec = 0
                a = self.cfg["ema_alpha"]            # adapt baseline only while quiet
                d = feat - self.mu; self.mu = self.mu + a * d
                self.var = np.maximum((1 - a) * self.var + a * d * d, 0.25)
        flagged = int(np.argmax(np.abs(r * self.mask)))
        return dict(score=score, thr=self.thr, active=self.active, started=started,
                    event=event or None, bin=flagged, freq=float(self.freqs[flagged]), z=z,
                    broadband_rejected=is_broadband and (score > self.thr))

    def flush(self, ts):
        """Close an in-progress event (end of file / shutdown) so it still gets logged."""
        if not self.active: return None
        ev = self._finish(ts); self.active = False; self.consec = self.quiet = 0
        return ev

    def _finish(self, ts_end):
        a = self.n - len(self.hist)
        lo = max(self.run_start - 6, a); hi = min(self.n, self.n - self.quiet + 6)
        Z = np.array([self.hist[i - a] for i in range(lo, hi)])
        b = int(np.argmax(np.abs(Z).mean(0)))
        col = Z[:, b]; peak = float(col.max())
        on = col > max(3.0, 0.5 * peak)
        dec = morse.decode_ook(on) if on.any() else dict(unit_frames=0, bits="", morse="", text="")
        return dict(start_ts=self.run_ts, end_ts=ts_end,
                    duration_s=round((hi - lo) / self.fps, 2),
                    freq_hz=float(self.freqs[b]), peak_score=round(self.peak, 1),
                    decoded_text=dec["text"], morse=dec["morse"], bits=dec["bits"],
                    keying_unit_s=round(dec["unit_frames"] / self.fps, 3))
