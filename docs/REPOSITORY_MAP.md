# Repository map

- `learning/` owns concise, dependency-ordered study guides and exercises.
- `foundation/` owns datasets, from-scratch educational code, and foundation experiments. It does not own agent runtime data.
- `atelier_agent/` owns the self-contained ReAct agent, RAG, tools, evaluations, adapters, and CLI.
- `atelier_agent/Project.md` remains the historical canonical filename because macOS treats `Project.md` and `PROJECT.md` as the same path; links and frozen task data use that spelling.
- `experiments/` owns cross-project metadata, templates, and the registry; it does not duplicate experiment artifacts.
- `benchmarks/` owns schemas and curated result summaries.
- `research/` owns reproductions, original ideas, and reports that are not tied to one implementation directory.
- `scripts/` owns repository-wide validation and summary utilities.
- `docs/` owns project-wide orientation, method, results, limits, and decisions.

Runtime data under `~/Atelier/` (or `ATELIER_HOME`) is the active local
operational state. `atelier_agent/data/` is retained only as development-era
legacy input and historical evidence; new runtime outputs remain external and
ignored.
