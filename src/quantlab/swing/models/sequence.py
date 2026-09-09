"""Sequence models over a window of bars (Model D).

A static feature row throws away the *order* of what happened. These engines
see the last ``seq_len`` bars as a multivariate sequence and are free to learn
that "volume rose while the range shrank, three bars running" differs from the
same values in another order.

Four inductive biases are available, and they are genuinely different:

* **GRU / LSTM** -- recurrent state, good at accumulating a condition over time.
* **TCN** -- dilated causal convolutions; fixed receptive field, no recurrence,
  far more parallel, and often stronger on short windows.
* **Transformer** -- self-attention over the window; the most expressive and by
  far the most data-hungry of the four.

At a few thousand training rows and a signal this weak, expressiveness is a
liability rather than an asset. Rather than assert that, the walk-forward runs
an architecture bake-off inside the *first* fold's training block -- which is a
subset of every later fold's training block, so the choice never sees data a
later fold has not already been given -- and carries the survivors forward. If
none of them beats the tabular models, the meta-learner is free to weight them
to nothing, and the report says so.

Causality: convolutions are left-padded, attention is causally masked, and each
window ends at bar t. A sequence ending at t contains no bar after t.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler

from .zoo import N_CLASSES, Engine, expand_proba

try:                                              # torch is optional
    import torch
    import torch.nn as nn

    TORCH_AVAILABLE = True
    torch.set_num_threads(4)
except Exception:                                 # pragma: no cover
    TORCH_AVAILABLE = False
    nn = object  # type: ignore


def _windows(mat: np.ndarray, seq_len: int) -> np.ndarray:
    """(n, d) -> (n, seq_len, d); window i ends at row i, front-padded."""
    pad = np.vstack([np.repeat(mat[:1], seq_len - 1, axis=0), mat])
    view = np.lib.stride_tricks.sliding_window_view(pad, seq_len, axis=0)  # (n, d, L)
    return np.ascontiguousarray(view.transpose(0, 2, 1))


if TORCH_AVAILABLE:

    class _GRUNet(nn.Module):
        def __init__(self, d, hidden=32, layers=1, dropout=0.2, cell="gru"):
            super().__init__()
            rnn = nn.GRU if cell == "gru" else nn.LSTM
            self.rnn = rnn(d, hidden, num_layers=layers, batch_first=True,
                           dropout=dropout if layers > 1 else 0.0)
            self.head = nn.Sequential(nn.Dropout(dropout), nn.Linear(hidden, N_CLASSES))

        def forward(self, x):
            out, _ = self.rnn(x)
            return self.head(out[:, -1])

    class _TCN(nn.Module):
        """Dilated causal convolutions: left-padding is what keeps it causal."""

        def __init__(self, d, channels=24, dropout=0.2, dilations=(1, 2, 4)):
            super().__init__()
            blocks, in_ch = [], d
            for dil in dilations:
                blocks.append(nn.Sequential(
                    nn.ConstantPad1d((2 * dil, 0), 0.0),
                    nn.Conv1d(in_ch, channels, kernel_size=3, dilation=dil),
                    nn.ReLU(), nn.Dropout(dropout),
                ))
                in_ch = channels
            self.net = nn.Sequential(*blocks)
            self.head = nn.Linear(channels, N_CLASSES)

        def forward(self, x):
            h = self.net(x.transpose(1, 2))
            return self.head(h[:, :, -1])

    class _Transformer(nn.Module):
        def __init__(self, d, model_dim=32, heads=4, layers=1, dropout=0.2, seq_len=20):
            super().__init__()
            self.proj = nn.Linear(d, model_dim)
            self.pos = nn.Parameter(torch.zeros(1, seq_len, model_dim))
            layer = nn.TransformerEncoderLayer(
                d_model=model_dim, nhead=heads, dim_feedforward=64,
                dropout=dropout, batch_first=True, norm_first=True,
            )
            self.enc = nn.TransformerEncoder(layer, num_layers=layers)
            self.head = nn.Sequential(nn.LayerNorm(model_dim), nn.Linear(model_dim, N_CLASSES))
            self.seq_len = seq_len

        def forward(self, x):
            h = self.proj(x) + self.pos[:, : x.shape[1]]
            mask = torch.triu(torch.ones(x.shape[1], x.shape[1], dtype=torch.bool), diagonal=1)
            h = self.enc(h, mask=mask)
            return self.head(h[:, -1])


class SequenceEngine(Engine):
    """A torch sequence model wrapped in the same interface as everything else."""

    def __init__(self, columns, arch: str = "gru", seq_len: int = 20, hidden: int = 32,
                 dropout: float = 0.2, lr: float = 4e-3, epochs: int = 50,
                 batch: int = 192, patience: int = 8, seed: int = 7):
        super().__init__(name=f"seq_{arch}", space="sequence", columns=columns)
        self.arch, self.seq_len, self.hidden = arch, seq_len, hidden
        self.dropout, self.lr, self.epochs = dropout, lr, epochs
        self.batch, self.patience, self.seed = batch, patience, seed
        self._imp = SimpleImputer(strategy="median")
        self._scaler = StandardScaler()

    # -- plumbing --------------------------------------------------------
    def _prep(self, X: pd.DataFrame, fit: bool) -> np.ndarray:
        raw = X.reindex(columns=self.columns).to_numpy(float)
        raw = np.nan_to_num(raw, nan=np.nan, posinf=np.nan, neginf=np.nan)
        raw = self._imp.fit_transform(raw) if fit else self._imp.transform(raw)
        raw = self._scaler.fit_transform(raw) if fit else self._scaler.transform(raw)
        return _windows(np.clip(raw, -8, 8), self.seq_len).astype(np.float32)

    def _build(self, d: int):
        if self.arch in ("gru", "lstm"):
            return _GRUNet(d, hidden=self.hidden, dropout=self.dropout, cell=self.arch)
        if self.arch == "tcn":
            return _TCN(d, channels=self.hidden, dropout=self.dropout)
        if self.arch == "transformer":
            return _Transformer(d, model_dim=self.hidden, dropout=self.dropout,
                                seq_len=self.seq_len)
        raise ValueError(f"unknown architecture: {self.arch!r}")

    # -- api -------------------------------------------------------------
    def fit(self, X, y, Xv=None, yv=None):
        if not TORCH_AVAILABLE:                     # pragma: no cover
            raise RuntimeError("torch is not installed")
        torch.manual_seed(self.seed)
        np.random.seed(self.seed)

        Z = self._prep(X, fit=True)
        yt = torch.tensor(np.asarray(y, dtype=np.int64))
        Zt = torch.tensor(Z)
        has_val = Xv is not None and len(Xv) > 40
        if has_val:
            Zv = torch.tensor(self._prep(Xv, fit=False))
            yvt = torch.tensor(np.asarray(yv, dtype=np.int64))

        self.model = self._build(Z.shape[2])
        opt = torch.optim.AdamW(self.model.parameters(), lr=self.lr, weight_decay=1e-4)
        # Class weights stop the net collapsing onto the majority outcome, which
        # at these base rates it otherwise does within a couple of epochs.
        counts = np.bincount(np.asarray(y, dtype=int), minlength=N_CLASSES).astype(float)
        weights = torch.tensor((counts.sum() / np.maximum(counts, 1)) ** 0.5, dtype=torch.float32)
        weights = weights / weights.mean()
        lossf = nn.CrossEntropyLoss(weight=weights)

        best, best_state, bad = np.inf, None, 0
        n = len(Zt)
        for epoch in range(self.epochs):
            self.model.train()
            perm = torch.randperm(n)
            for i in range(0, n, self.batch):
                idx = perm[i : i + self.batch]
                opt.zero_grad()
                loss = lossf(self.model(Zt[idx]), yt[idx])
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
                opt.step()
            if not has_val:
                continue
            self.model.eval()
            with torch.no_grad():
                vloss = float(lossf(self.model(Zv), yvt))
            if vloss < best - 1e-4:
                best, bad = vloss, 0
                best_state = {k: v.clone() for k, v in self.model.state_dict().items()}
            else:
                bad += 1
                if bad >= self.patience:
                    break
        if best_state is not None:
            self.model.load_state_dict(best_state)
        self.meta.update({"val_loss": best if np.isfinite(best) else None,
                          "epochs_run": epoch + 1, "arch": self.arch,
                          "seq_len": self.seq_len})
        return self

    def predict_proba(self, X):
        self.model.eval()
        Z = torch.tensor(self._prep(X, fit=False))
        with torch.no_grad():
            logits = self.model(Z)
            p = torch.softmax(logits, dim=1).numpy()
        return expand_proba(p, np.arange(N_CLASSES))
