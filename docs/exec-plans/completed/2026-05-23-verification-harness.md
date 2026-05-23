# Verification Harness Completion

Date: 2026-05-23

## Outcome

The verification-harness tranche is complete for the current declared product model.

The repository now has checked-in executable coverage for:

- fixture-backed backend contract interpretation
- sensor projection for canonical `signed_in`, `signed_out`, and `unknown`
- sign-in and sign-out routing behavior
- config-flow site selection and reconfiguration drift handling
- persisted-session recovery after restart-like setup
- post-mutation coordinator refresh and state verification
- admin-facing drift issue surfacing without durable-config mutation
- open-ended configured-location persistence with per-location coordinate behavior
- compatibility-hint ambiguity rules
- legacy config-entry migration onto `configured_locations`

## Checked-in evidence

Primary harness surfaces:

- [tests/test_logic.py](../../../tests/test_logic.py)
- [tests/test_runtime.py](../../../tests/test_runtime.py)
- [tests/test_config_flow.py](../../../tests/test_config_flow.py)
- [tests/test_lifecycle.py](../../../tests/test_lifecycle.py)
- [tests/fixtures/config_v2](../../../tests/fixtures/config_v2)
- [.github/workflows/python-tests.yml](../../../.github/workflows/python-tests.yml)

Canonical behavior and model docs:

- [GLOSSARY.md](../../../GLOSSARY.md)
- [ARCHITECTURE.md](../../../ARCHITECTURE.md)
- [docs/RELIABILITY.md](../../RELIABILITY.md)
- [docs/decisions/2026-05-23-open-ended-location-model.md](../../decisions/2026-05-23-open-ended-location-model.md)

## Notes

- Windows lifecycle verification still requires Home Assistant test-environment shims for `aiodns` selector-loop behavior and `os.fchmod`.
- Any future routing-semantic expansion must start from a concrete Sign In App scenario and a new explicit decision.
