# 08 — Agents and tool use

**Concept.** ReAct alternates model decisions and tool observations. Retrieval supplies context; structured outputs constrain actions; tests verify edits; routing and escalation manage cost and risk. **Background.** The earlier modules plus basic software testing.

**Task.** Read `atelier_agent/agent/react.py`, trace one tool call, and run the sample task with mocked or local components. **Verify.** A code change is accepted only after the test runner is green. **Mistakes.** Trusting model text without verification, allowing path drift, and compounding unchecked errors.

**Production connection.** This module maps directly to the existing ReAct loop, registry, RAG, memory, and eval suites. **Read.** [Current Atelier results](../../docs/CURRENT_RESULTS.md). **Exit.** Name the observable signal that makes an agent result trustworthy.
