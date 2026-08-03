"""Tiny offline dataset utilities."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TextDataset:
    ids: list[int]
    block_size: int

    def __len__(self) -> int:
        return max(0, len(self.ids) - self.block_size)

    def get(self, index: int):
        """Return input and next-token target windows as tensors."""
        import torch

        x = torch.tensor(self.ids[index : index + self.block_size], dtype=torch.long)
        y = torch.tensor(self.ids[index + 1 : index + self.block_size + 1], dtype=torch.long)
        return x, y


def split_ids(ids: list[int], fraction: float = 0.9) -> tuple[list[int], list[int]]:
    """Split a token stream without downloading or shuffling it."""
    cut = int(len(ids) * fraction)
    return ids[:cut], ids[cut:]
