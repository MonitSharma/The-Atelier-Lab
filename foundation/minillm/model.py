"""A deliberately small transformer language model."""

from __future__ import annotations

from dataclasses import dataclass

import torch
from torch import Tensor, nn

from .attention import CausalSelfAttention


@dataclass(frozen=True)
class ModelConfig:
    vocab_size: int
    block_size: int = 64
    dim: int = 64
    heads: int = 4
    layers: int = 2


class TransformerBlock(nn.Module):
    def __init__(self, config: ModelConfig) -> None:
        super().__init__()
        self.norm1 = nn.LayerNorm(config.dim)
        self.attn = CausalSelfAttention(config.dim, config.heads)
        self.norm2 = nn.LayerNorm(config.dim)
        self.ff = nn.Sequential(nn.Linear(config.dim, 4 * config.dim), nn.GELU(), nn.Linear(4 * config.dim, config.dim))

    def forward(self, x: Tensor) -> Tensor:
        x = x + self.attn(self.norm1(x))
        return x + self.ff(self.norm2(x))


class TransformerLM(nn.Module):
    def __init__(self, config: ModelConfig) -> None:
        super().__init__()
        self.config = config
        self.token_embedding = nn.Embedding(config.vocab_size, config.dim)
        self.position_embedding = nn.Embedding(config.block_size, config.dim)
        self.blocks = nn.Sequential(*(TransformerBlock(config) for _ in range(config.layers)))
        self.norm = nn.LayerNorm(config.dim)
        self.lm_head = nn.Linear(config.dim, config.vocab_size, bias=False)
        self.lm_head.weight = self.token_embedding.weight

    def forward(self, idx: Tensor, targets: Tensor | None = None) -> tuple[Tensor, Tensor | None]:
        _, t = idx.shape
        if t > self.config.block_size:
            raise ValueError("sequence exceeds block_size")
        pos = torch.arange(t, device=idx.device)
        x = self.token_embedding(idx) + self.position_embedding(pos)[None, :, :]
        logits = self.lm_head(self.norm(self.blocks(x)))
        loss = None if targets is None else nn.functional.cross_entropy(logits.view(-1, logits.size(-1)), targets.view(-1))
        return logits, loss

    @torch.no_grad()
    def generate(self, idx: Tensor, steps: int, temperature: float = 1.0) -> Tensor:
        for _ in range(steps):
            context = idx[:, -self.config.block_size :]
            logits, _ = self(context)
            probs = (logits[:, -1, :] / temperature).softmax(-1)
            idx = torch.cat((idx, torch.multinomial(probs, 1)), dim=1)
        return idx
