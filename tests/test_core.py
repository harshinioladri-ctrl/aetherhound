import unittest
import numpy as np
from aetherhound import morse, config as C, dsp
from aetherhound.sources import SimSource
from aetherhound.detector import Detector
from aetherhound.models import TorchAE, StatModel, have_torch

def run_sim(msg="SECRET", inject=6.0, secs=20, train_secs=25, model="stat"):
    cfg = C.load()
    cfg["model"] = model
    tr = SimSource()
    fps = 48000 / 1024
    X = [dsp.features(tr.read(), 1024, 64) for _ in range(int(train_secs * fps))]
    fr = dsp.bin_freqs(48000, 0, 1024, 64)
    d = Detector(cfg, fr, fps)
    d.fit(np.array(X))
    s = SimSource(inject_after=inject, message=msg, seed=7)
    ev = []
    for _ in range(int(secs * fps)):
        r = d.process(dsp.features(s.read(), 1024, 64), 0.0)
        if r["event"]:
            ev.append(r["event"])
    return ev

class TestAetherHoundCore(unittest.TestCase):
    def test_morse_roundtrip(self):
        """Validates Morse code encoding and OOK demodulation."""
        test_strings = ["SOS 73", "HELLO WORLD", "PASSWORD 42"]
        for s in test_strings:
            env = morse.encode_envelope(s, unit_samples=5)
            decoded = morse.decode_ook(env)["text"]
            self.assertEqual(decoded, s)

    def test_no_false_positive_on_quiet_baseline(self):
        """Ensures that normal server room hum generates 0 false alerts."""
        self.assertEqual(run_sim(inject=999.0), [])

    def test_broadband_impulse_rejection(self):
        """Week 4: Rejects wideband transients (door slams, coughing) while detecting narrowband covert signals."""
        cfg = C.load()
        cfg["model"] = "stat"
        fr = dsp.bin_freqs(48000, 0, 1024, 64)
        det = Detector(cfg, fr, 48000 / 1024)
        baseline = np.random.normal(-40.0, 1.0, (100, 64))
        det.fit(baseline)
        
        # 1. Wideband impulse (door slam): power increases equally across all bins
        wideband_slam = np.ones(64) * 10.0
        res_slam = det.process(wideband_slam, 0.0)
        self.assertFalse(res_slam["active"])  # Must NOT trigger alert!
        self.assertTrue(res_slam.get("broadband_rejected", False))
        
        # 2. Narrowband covert channel (signal concentrated in 1 bin)
        narrowband_signal = np.ones(64) * -40.0
        narrowband_signal[32] = 20.0  # Sharp spike in bin 32
        # Feed multiple frames to satisfy persistence
        for _ in range(det.cfg["persist"] + 1):
            res_signal = det.process(narrowband_signal, 0.0)
        self.assertTrue(res_signal["active"])
        self.assertEqual(res_signal["bin"], 32)

    def test_detects_and_decodes_stat_model(self):
        """Tests end-to-end detection and Morse decode using statistical z-score model."""
        ev = run_sim(model="stat")
        self.assertEqual(len(ev), 1)
        self.assertAlmostEqual(ev[0]["freq_hz"], 18000, delta=600)
        self.assertEqual(ev[0]["decoded_text"], "SECRET")

    def test_dsp_feature_geometry(self):
        """Verifies Welch PSD feature vector dimensions and frequencies."""
        block = np.zeros(1024)
        feat = dsp.features(block, 1024, 64)
        self.assertEqual(len(feat), 64)
        freqs = dsp.bin_freqs(48000, 0, 1024, 64)
        self.assertEqual(len(freqs), 64)
        self.assertGreater(freqs[-1], freqs[0])

    @unittest.skipUnless(have_torch(), "PyTorch not available")
    def test_pytorch_autoencoder_training(self):
        """Week 3: Deep Autoencoder trains and achieves low reconstruction loss."""
        ae = TorchAE(nbins=64, epochs=20, hidden=32, code=8)
        X = np.random.normal(0, 1, (100, 64))
        loss_hist = ae.fit(X)
        self.assertGreater(len(loss_hist), 0)
        self.assertLess(loss_hist[-1], loss_hist[0])

if __name__ == "__main__":
    unittest.main()
