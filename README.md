<p align="center">
  <img src="custom_components/signinapp/brand/logo.png" alt="Sign In App logo" width="320" />
</p>

# Home Assistant Sign In App Integration

This repository provides a Home Assistant custom integration for Sign In App, focused on attendance automation and work-location-aware sign-in and sign-out flows.

## What It Does

The integration connects Home Assistant to Sign In App so you can see attendance state, automate sign-in and sign-out actions, and route those actions against configured work locations.

## Core Features

- config-flow authentication using a companion code
- configured work-location selection
- `signinapp.sign_in` and `signinapp.sign_out` services
- polling sensor for signed-in, signed-out, and unknown state
- per-location routing behavior stored in the integration configuration

## Installation

### Preferred: HACS

1. Open **HACS -> Integrations**.
2. Open the three-dot menu and choose **Custom repositories**.
3. Add this repository URL and choose **Integration**.
4. Install **Sign In App**.
5. Restart Home Assistant.

### Fallback: Manual

1. Copy `custom_components/signinapp` into your Home Assistant `custom_components` directory.
2. Restart Home Assistant.

## Setup

1. Open **Settings -> Devices & Services**.
2. Add the **Sign In App** integration.
3. Enter a companion code.
4. Choose the work locations the integration should manage.
5. Select the Home Assistant `person` entity that represents the user.

## Documentation

Start with:

- [ARCHITECTURE.md](ARCHITECTURE.md)
- [docs/PRODUCT_SENSE.md](docs/PRODUCT_SENSE.md)
- [docs/RELIABILITY.md](docs/RELIABILITY.md)

For repository workflow and agent-focused context, read [AGENTS.md](AGENTS.md).
