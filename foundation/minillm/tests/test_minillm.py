import pytest

torch = pytest.importorskip("torch")

from foundation.minillm.attention import scaled_dot_product_attention
from foundation.minillm.model import ModelConfig, TransformerLM
from foundation.minillm.tokenizer import ByteTokenizer, CharTokenizer


def test_tokenizers_round_trip():
    text = "hello, नमस्ते"
    assert CharTokenizer(text).decode(CharTokenizer(text).encode(text)) == text
    tokenizer = ByteTokenizer()
    assert tokenizer.decode(tokenizer.encode(text)) == text


def test_causal_attention_does_not_see_future():
    q = k = v = torch.randn(1, 1, 4, 8)
    first = scaled_dot_product_attention(q, k, v)
    changed = v.clone()
    changed[:, :, 3, :] += 100
    second = scaled_dot_product_attention(q, k, changed)
    assert torch.allclose(first[:, :, :3], second[:, :, :3])


def test_transformer_shapes_and_loss():
    torch.manual_seed(0)
    model = TransformerLM(ModelConfig(vocab_size=17, block_size=8, dim=16, heads=4, layers=1))
    x = torch.randint(0, 17, (2, 8))
    logits, loss = model(x, x)
    assert logits.shape == (2, 8, 17)
    assert loss is not None and torch.isfinite(loss)
