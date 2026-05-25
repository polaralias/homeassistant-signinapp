<p align="center">
  <img src="custom_components/signinapp/brand/logo.png" alt="Sign In App logo" width="320" />
</p>

# Home Assistant Sign In App Integration

This repository contains a Home Assistant custom integration for Sign In App.

Its product purpose is reliable Sign In App attendance automation and state visibility through Home Assistant.

The project goal is:

- let Home Assistant know whether a user is signed in or out of Sign In App
- let Home Assistant sign users in and out across their supported work locations
- make attendance across user work locations automatable from Home Assistant presence and scripts
- provide a first-class setup flow for account connection, work location selection, and attendance routing behavior

This repository is a test-backed, documented Home Assistant custom integration for Sign In App.

## What exists today

- Home Assistant config flow authentication using a companion code
- backend-discovered configured-location selection with inclusion and label override fields
- per-location `coordinate_behavior` stored durably and used for runtime location resolution
- concrete `site_id` action input support, with legacy `site_type` hints retained for compatibility
- compatibility `site_type` hints now require a unique configured match or active-session disambiguation; they no longer pick the first matching target
- `signinapp.sign_in` and `signinapp.sign_out` services
- a polling sensor with canonical `signed_in` / `signed_out` / `unknown` state classes
- sanitized fixture-backed logic harness for the reverse-engineered backend contract
- CI that runs the checked-in regression harness on every push and pull request

Current product boundary:

- `site_id` is the primary action surface
- `site_type` remains supported as a compatibility-only hint surface
- per-location routing semantics are intentionally limited to `device_tracker` and `remote_zero`

## Start here

- Maintainer rules: [AGENTS.md](AGENTS.md)
- Domain language: [GLOSSARY.md](GLOSSARY.md)
- Contributor guide: [CONTRIBUTING.md](CONTRIBUTING.md)
- Architecture: [ARCHITECTURE.md](ARCHITECTURE.md)
- Product intent: [docs/PRODUCT_SENSE.md](docs/PRODUCT_SENSE.md)
- Reliability goals: [docs/RELIABILITY.md](docs/RELIABILITY.md)
- Security model: [docs/SECURITY.md](docs/SECURITY.md)
- Active execution plans: [docs/PLANS.md](docs/PLANS.md)

## Installation

### HACS

1. Open **HACS -> Integrations**.
2. Open the three-dot menu and choose **Custom repositories**.
3. Add this repository URL and choose **Integration**.
4. Install **Sign In App**.
5. Restart Home Assistant.

### Manual

1. Copy `custom_components/signinapp` into your Home Assistant `custom_components` directory.
2. Restart Home Assistant.

## Configuration

1. In Home Assistant, open `Settings -> Devices & Services`.
2. Add the `Sign In App` integration.
3. Enter a companion code.
4. Configure the work locations the integration should manage for the user.
5. Select the `person` entity that represents the user.

## Current status

The development harness now lives in [tests/test_logic.py](tests/test_logic.py), [tests/test_runtime.py](tests/test_runtime.py), [tests/test_config_flow.py](tests/test_config_flow.py), [tests/test_lifecycle.py](tests/test_lifecycle.py), [tests/fixtures/config_v2](tests/fixtures/config_v2), and [.github/workflows/python-tests.yml](.github/workflows/python-tests.yml).

Run it locally with:

```powershell
python -m unittest discover -s tests -p "test_*.py"
```

On Windows, the full Home Assistant lifecycle module can take several minutes to complete.

Read the completed harness note in [docs/exec-plans/completed/2026-05-23-verification-harness.md](docs/exec-plans/completed/2026-05-23-verification-harness.md). Supporting observed evidence remains under [docs/references](docs/references).
