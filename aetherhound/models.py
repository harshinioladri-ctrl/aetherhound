"""Anomaly models. Both expose residual(z) -> per-bin residual (same shape as z),
so the detector can score and also pinpoint the offending frequency bin.
"""
import os, json
import numpy as np

class StatModel:
    """Per-bin robust z-score statistical model (no ML deps).
    Ideal for ultra-lightweight edge hardware (e.g., Raspberry Pi Zero)."""
    kind = "stat"
    def fit(self, Z): pass
    def residual(self, z): return z
    def save(self, path): pass
    def load(self, path, nbins): pass

class TorchAE:
    """Deep autoencoder trained solely on 'normal' server emissions.
    Compresses baseline spectral features into an information bottleneck (latent space).
    Normal server hum reconstructs with low residual; artificial structured transmissions
    (Morse / binary pulsing) fail reconstruction, producing high residuals that pinpoint the frequency.
    """
    kind = "ae"
    def __init__(self, nbins, epochs=200, hidden=48, code=12, lr=3e-3):
        import torch, torch.nn as nn
        self.t = torch
        self.nbins = nbins
        self.epochs = epochs
        self.loss_history = []
        
        # Deep Autoencoder Architecture:
        # Encoder: nbins -> hidden -> code
        # Decoder: code -> hidden -> nbins
        self.net = nn.Sequential(
            nn.Linear(nbins, hidden),
            nn.BatchNorm1d(hidden),
            nn.ReLU(),
            nn.Linear(hidden, code),
            nn.ReLU(),
            nn.Linear(code, hidden),
            nn.BatchNorm1d(hidden),
            nn.ReLU(),
            nn.Linear(hidden, nbins)
        )

    def fit(self, Z, verbose=False):
        t = self.t
        X = t.tensor(Z, dtype=t.float32)
        batch_size = min(256, max(16, len(X) // 4))
        
        opt = t.optim.AdamW(self.net.parameters(), lr=3e-3, weight_decay=1e-4)
        scheduler = t.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=self.epochs, eta_min=1e-4)
        loss_fn = t.nn.MSELoss()
        t.manual_seed(42)
        
        self.net.train()
        self.loss_history = []
        
        for epoch in range(self.epochs):
            perm = t.randperm(len(X))
            epoch_loss = 0.0
            steps = 0
            for i in range(0, len(X), batch_size):
                b = X[perm[i:i + batch_size]]
                if len(b) <= 1: continue  # Skip single-sample batch for batchnorm
                opt.zero_grad()
                loss = loss_fn(self.net(b), b)
                loss.backward()
                opt.step()
                epoch_loss += float(loss.item())
                steps += 1
            scheduler.step()
            avg_loss = epoch_loss / max(1, steps)
            self.loss_history.append(avg_loss)
            if verbose and (epoch % max(1, self.epochs // 10) == 0 or epoch == self.epochs - 1):
                print(f"    Epoch {epoch+1}/{self.epochs} - Reconstruction Loss (MSE): {avg_loss:.6f}")
                
        self.net.eval()
        return self.loss_history

    def residual(self, z):
        t = self.t
        self.net.eval()
        with t.no_grad():
            # If 1D single frame
            if z.ndim == 1:
                x = t.tensor(z.reshape(1, -1), dtype=t.float32)
                recon = self.net(x).numpy()[0]
                return z - recon
            else:
                x = t.tensor(z, dtype=t.float32)
                recon = self.net(x).numpy()
                return z - recon

    def save(self, path):
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self.t.save(self.net.state_dict(), path)
        loss_path = path + ".loss.json"
        with open(loss_path, "w") as f:
            json.dump({"loss_history": self.loss_history}, f)

    def load(self, path, nbins):
        try:
            state = self.t.load(path, weights_only=True)
        except TypeError:
            state = self.t.load(path)
        self.net.load_state_dict(state)
        self.net.eval()

def have_torch():
    try:
        import torch  # noqa
        return True
    except Exception:
        return False

def make_model(kind, nbins):
    if kind == "auto":
        kind = "ae" if have_torch() else "stat"
    return TorchAE(nbins) if kind == "ae" else StatModel()
