# Step 06 — Code and Repository Intelligence v1

Status: **PASS — deterministic repository inspection implemented**

## Delivered

`repo.inspector.RepositoryInspector` provides a model-free profile containing:

- Git root, branch, commit, clean/dirty status, history, and diff;
- file count and truncation state;
- language counts;
- Python, JavaScript/TypeScript, Rust, C/C++, and common build/environment
  markers;
- package managers and dependency files;
- pytest, JavaScript, Cargo, and CTest detection;
- Python, Node, and Cargo entry points;
- symbols and imports using AST or conservative language regexes;
- heuristic test-to-source relationships;
- deterministic important-file scores and reasons;
- bounded regex search with file/line evidence.

## Interfaces

```bash
atelier repo inspect PATH
atelier repo status PATH
atelier repo symbols PATH
atelier repo search PATTERN --path PATH
atelier repo tests PATH [--run]
```

The agent registry also exposes `repo_inspect`, `repo_status`, `repo_symbols`,
`repo_search`, and `repo_tests`. These tools receive the Step 05 approved
workspace context and do not embed source files into the scientific library.

## Fixture verification

The frozen fixture contains a Python package with seven files, a pyproject entry
point, source symbols/imports, and a test importing the source module. The
inspector reports:

```text
files: 7
languages: Python 5, Markdown 1, TOML 1
package manager: Python / pyproject
test framework: pytest
entry points: 1
test-to-source relationships: 1
search `def add`: 1 exact file/line hit
```

The fixture is intentionally multi-file and cross-links tests to source; it is
not a single-file repair task and does not invoke a model.

## Boundaries

The inspector is structural evidence, not semantic code correctness. It uses
AST parsing for Python and conservative regexes for other languages. Full
dependency graphs, compiler-grade references, and selective semantic indexing
remain future improvements after the baseline is benchmarked.
