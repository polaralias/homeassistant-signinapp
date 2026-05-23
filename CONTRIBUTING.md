# Contributing

## Local test command

Run the checked-in harness with:

```powershell
python -m unittest discover -s tests -p "test_*.py"
```

On Windows, expect the lifecycle module to dominate runtime. The full command is still the canonical publish-check, but it may take several minutes.

## What the harness covers

The repository test suite includes:

- pure logic regression tests
- runtime service and sensor tests
- config-flow tests
- Home Assistant lifecycle tests

Read [docs/exec-plans/completed/2026-05-23-verification-harness.md](docs/exec-plans/completed/2026-05-23-verification-harness.md) for the completed harness scope.

## Windows notes

On Windows, the Home Assistant lifecycle tests rely on test-environment shims required by Home Assistant and its dependencies:

- selector-loop policy for `aiodns`
- `os.fchmod` shim for Home Assistant storage writes

These are treated as test-environment requirements, not integration defects.

## Contribution rules

- prefer small test-backed changes
- preserve sanitized contract evidence
- update canonical docs when product behavior changes
- do not store secrets, companion codes, or unsanitized captures in the repo
