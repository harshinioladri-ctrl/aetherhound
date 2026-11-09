import time
from . import dsp
from .detector import Detector
from .eventlog import EventLog
from .alerts import Alerter

class Engine:
    def __init__(self, cfg, src, det):
        self.cfg, self.src, self.det = cfg, src, det
        self.log = EventLog(cfg["log_dir"]); self.alert = Alerter(cfg)
        self.events = []; self.frames = 0
    def feat(self):
        return dsp.features(self.src.read(), self.cfg["frame"], self.cfg["nbins"], self.src.is_complex)
    def step(self):
        feat = self.feat(); self.frames += 1
        res = self.det.process(feat, time.time()); res["feat"] = feat
        if res["started"]: self.alert.fire()
        if res["event"]:
            row = self.log.write(res["event"]); self.events.append(row)
        return res

    def flush(self):
        import time as _t
        ev = self.det.flush(_t.time())
        if ev: self.events.append(self.log.write(ev))
        return ev

def make_detector_geometry(src, cfg):
    freqs = dsp.bin_freqs(src.fs, src.center, cfg["frame"], cfg["nbins"], src.is_complex)
    fps = src.fs / src.block
    return freqs, fps
