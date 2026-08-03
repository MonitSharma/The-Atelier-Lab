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
