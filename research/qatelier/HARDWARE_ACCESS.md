# Quantum provider access checkpoint

> Checked: 2026-08-10 11:01 +08, on branch `qatelier`.
>
> No quantum circuit was submitted. No QPU shots or HQCs were consumed.

## Environment

The repository `.venv-qatelier` is an isolated Python 3.11 environment on
Apple Silicon. The optional provider stack is installed there and recorded in
[`requirements-quantum.txt`](requirements-quantum.txt):

- Qiskit, Qiskit Aer, and `qiskit-ibm-runtime`;
- pytket, `pytket-qiskit`, and `pytket-quantinuum`;
- Quantinuum `qnexus` and its required `selene-core` runtime dependency.

Import checks passed for all of the above provider-facing modules, and
`uv pip check` passes in `.venv-qatelier`. The shared repository `.venv` has
an unavoidable version conflict between Atelier's `rich>=14` requirement and
`qnexus 0.48.0`'s `rich<14` requirement; the provider stack is isolated so
this does not alter the main project's dependency environment.

## IBM Quantum

The root `.env` contains both `QISKIT_IBM_TOKEN` and `QISKIT_IBM_INSTANCE`.
The token value was not printed or committed. A direct
`QiskitRuntimeService` authentication check succeeded, and the configured
instance can list three IBM hardware backends:

| Backend | Operational flag | Reported status | Pending jobs |
| --- | ---: | --- | ---: |
| `ibm_fez` | true | active | 438 |
| `ibm_marrakesh` | true | maintenance | 30 |
| `ibm_kingston` | true | active | 368 |

This verifies that the IBM credentials are valid and that the instance can
see hardware metadata. It does not reserve a device or guarantee immediate
queue access; queue lengths and maintenance state are time-dependent.

## Quantinuum / Nexus

`qnexus.auth.is_logged_in()` returned `True`, so a valid local Nexus login
token is already available. The account query also returned 21 accessible
projects. The device catalogue exposes both the `H2-2` and `Helios-1`
hardware families, along with their emulators and syntax checkers.

The non-submitting real-time status checks returned:

| Device | Status at checkpoint |
| --- | --- |
| `H2-2` | offline |
| `Helios-1` | online |
| `H2-2E` | online |
| `Helios-1E` | online |

The quota endpoint returned `compilation`, `simulation`, `jupyterhub`, and
`database_usage`, but each displayed `No quota set for user` rather than a
numeric HQC allowance. Therefore the account is linked and authenticated,
and Helios is currently reported online, but this check does not prove that
the account has spendable hardware HQCs or permission to submit to every
hardware target. That must be confirmed in Nexus or by an explicitly
authorized, tiny pilot submission later.

The check emitted a deprecation warning for the quota API endpoint used by
the installed `qnexus` client. The installed client is `qnexus 0.48.0`, and
an upgrade dry-run did not select a newer `qnexus` release at this checkpoint.
This should be rechecked before the first hardware run.

## Security and next step

- `.env` files remain ignored by Git and their local permissions were tightened
  to owner-only read/write (`0600`).
- No credentials, tokens, project identifiers, or provider job IDs were added
  to the repository.
- The next safe step is a simulator-only smoke test. Hardware execution should
  wait until the first circuit, shot budget, backend, and HQC authorization are
  frozen in the experiment manifest.

Provider workflows referenced during this check:

- [IBM Quantum account initialization](https://quantum.cloud.ibm.com/docs/en/guides/initialize-account)
- [Quantinuum Nexus getting started](https://docs.quantinuum.com/nexus/trainings/notebooks/basics/getting_started.html)
- [Quantinuum Nexus quotas](https://docs.quantinuum.com/nexus/trainings/notebooks/basics/auth_quotas.html)
- [Quantinuum backends](https://docs.quantinuum.com/nexus/user_guide/concepts/backends.html)
