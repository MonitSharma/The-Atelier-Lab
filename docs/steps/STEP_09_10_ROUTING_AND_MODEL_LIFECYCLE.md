# Steps 09–10 — Capability Router and Model Lifecycle

Status: **complete**

## Capability-first routing

`agent.capability_router.CapabilityRouter` classifies a task into paper, code,
data, vision, research, quantum, optimization, or general before selecting a
model. A route decision includes the workflow and model role, modality and
tools, difficulty and context budget, workspace privacy and network requirement,
memory use, abstention, and escalation conditions.

The router is deterministic and local. Repository work selects the benchmarked
`coder` and `code_fix`; paper work selects fast or deep reading; and a request
for web lookup in a `LOCAL_ONLY` workspace abstains instead of leaking the task
externally.

```bash
atelier route "Fix the failing tests in this repository"
atelier route "Search the web for the latest DOI"
```

## Model lifecycle

`models.lifecycle.ModelLifecycle` is the role-aware inventory for the local
stack. It records configured role, model ID, quantization estimate,
memory/context budget, modality, tool/JSON support, installed state, and
current Ollama residency. Memory values are planning estimates; host-level
measurements remain a Step 24 responsibility.

```bash
atelier models list
atelier models status --json
atelier models bench --model qwen3:8b --max-steps 14
```

The benchmark command is explicit and one-model-at-a-time. A model is not
downloaded merely to populate the registry; placeholders remain visible as
missing rather than being silently installed.

The capability layer also has a frozen 16-case human-labeled evaluation:

```bash
atelier route-eval
```

The current heuristic router scores 16/16 for domain, workflow, and
`LOCAL_ONLY` abstention on that development set. The set is intentionally
small and frozen; larger held-out routing cases remain part of reliability
expansion.

## Verification

Tests cover code routing to the benchmarked coder, LOCAL_ONLY abstention, paper
memory selection, and merging configured roles with mocked local Ollama state.
