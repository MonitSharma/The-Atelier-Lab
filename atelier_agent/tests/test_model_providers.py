import sys
from types import SimpleNamespace

from models.ollama_provider import OllamaProvider
from models.types import GenerationResult, ModelSpec


class FakeProvider:
    def generate(self, messages, spec, *, temperature, json_mode=False, think=False):
        return GenerationResult(text="ok", model_name=spec.model_id)

    def stream(self, messages, spec, *, temperature):
        yield "o"
        yield "k"


def test_provider_contract_can_be_mocked():
    provider = FakeProvider()
    spec = ModelSpec("worker", "fake", "local-test", "worker")
    assert provider.generate([], spec, temperature=0).text == "ok"
    assert "".join(provider.stream([], spec, temperature=0)) == "ok"


def test_ollama_provider_passes_json_schema(monkeypatch):
    calls = []

    class Client:
        def __init__(self, host):
            pass

        def chat(self, **kwargs):
            calls.append(kwargs)
            return {"message": {"content": '{"ok": true}'}}

    monkeypatch.setitem(sys.modules, "ollama", SimpleNamespace(Client=Client))
    provider = OllamaProvider("http://localhost:11434")
    schema = {"type": "object", "properties": {"ok": {"type": "boolean"}}}
    provider.generate([], ModelSpec("worker", "ollama", "local", "worker"),
                     temperature=0, json_mode=True, json_schema=schema)
    assert calls[0]["format"] == schema
