"""Minimal deterministic-enough CPU training and checkpoint helpers."""

from __future__ import annotations

from pathlib import Path

import torch

from .model import TransformerLM


def train_step(model: TransformerLM, optimizer: torch.optim.Optimizer, x: torch.Tensor, y: torch.Tensor) -> float:
    optimizer.zero_grad(set_to_none=True)
    _, loss = model(x, y)
    assert loss is not None
    loss.backward()
    optimizer.step()
    return float(loss.detach())


def save_checkpoint(model: TransformerLM, optimizer: torch.optim.Optimizer, path: str | Path) -> None:
    torch.save({"model": model.state_dict(), "optimizer": optimizer.state_dict(), "config": model.config.__dict__}, path)


def load_checkpoint(model: TransformerLM, optimizer: torch.optim.Optimizer, path: str | Path) -> None:
    state = torch.load(path, map_location="cpu", weights_only=False)
    model.load_state_dict(state["model"])
    optimizer.load_state_dict(state["optimizer"])
