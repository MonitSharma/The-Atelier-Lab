"""Readable causal attention primitives."""

from __future__ import annotations

import math

import torch
from torch import Tensor, nn


def scaled_dot_product_attention(q: Tensor, k: Tensor, v: Tensor, causal: bool = True) -> Tensor:
    """Compute softmax(QKᵀ / √d)V; q/k/v are (B, H, T, D)."""
    scores = q @ k.transpose(-2, -1) / math.sqrt(q.size(-1))  # (B,H,T,T)
    if causal:
        mask = torch.triu(torch.ones(scores.shape[-2:], dtype=torch.bool, device=scores.device), 1)
        scores = scores.masked_fill(mask, float("-inf"))
    return scores.softmax(dim=-1) @ v


class CausalSelfAttention(nn.Module):
    """Multi-head self-attention with a causal mask."""

    def __init__(self, dim: int, heads: int) -> None:
        super().__init__()
        if dim % heads:
            raise ValueError("dim must be divisible by heads")
        self.heads = heads
        self.head_dim = dim // heads
        self.qkv = nn.Linear(dim, 3 * dim)
        self.out = nn.Linear(dim, dim)

    def forward(self, x: Tensor) -> Tensor:
        b, t, d = x.shape
        q, k, v = self.qkv(x).chunk(3, dim=-1)
        shape = (b, t, self.heads, self.head_dim)
        q, k, v = (z.view(shape).transpose(1, 2) for z in (q, k, v))
        y = scaled_dot_product_attention(q, k, v).transpose(1, 2).contiguous().view(b, t, d)
        return self.out(y)
