---
type: "Repository Guide"
title: "Home Assistant Sign In App Integration"
description: "Documents Home Assistant Sign In App Integration for the homeassistant-signinapp repository."
timestamp: 2026-07-28T21:55:36Z
authority: canonical
verification: untested
owner: polaralias
tags:
  - homeassistant-signinapp
  - repository-guide
navigation:
  role: entry-point
  order: 10
---
<p align="center">
  <img src="Sign%20In%20App%20Banner.png" alt="Sign In App banner" width="960" />
</p>

# Home Assistant Sign In App Integration

This repository provides a Home Assistant custom integration for Sign In App, focussed on attendance automation and work-location-aware sign-in and sign-out flows.

## What It Does

The integration connects Home Assistant to Sign In App so you can see attendance state, automate sign-in and sign-out actions, and route those actions against configured work locations.

## Core Features

- config-flow authentication using a companion code
- configured work-location selection
- `signinapp.sign_in` and `signinapp.sign_out` services
- polling sensor for signed-in, signed-out, and unknown state
- per-location routing behaviour stored in the integration configuration
- API-backed daily, weekly and monthly attendance and activity reports
- configurable quota periods, progress, remaining time and overtime
- optional quota rollups and country/region or custom holiday adjustments

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

### Attendance reporting

Open the integration's **Configure** options to set quota hours, period length/unit,
anchor date and workdays. The default is 37.5 hours per week, counting working
activities only. Select N days, weeks or months for other contracts. Weekly anchors
must be Mondays; monthly anchors must be the first of a month.

Quota rollups and holiday adjustments are separate opt-ins. Select a country and
region, or leave the country blank and enter custom ISO holiday dates. Holiday
hours reduce the quota rather than increasing the remaining workdays' requirements.

The companion account must have permission to view its own sign-in history.
Current attendance remains available when history permission is missing. Reports
include exact hours; daily secondary metrics and activity percentages are available
as disabled entities to enable as needed. See the [reporting contract](docs/product-specs/attendance-reporting.md)
for period, classification and quota semantics.

## Documentation

- [Automation and dashboard examples](examples/README.md): native zones, Custom
  Zone polygons, notifications, cumulative totals and expandable reporting cards.

Start with:

- [ARCHITECTURE.md](ARCHITECTURE.md)
- [docs/PRODUCT_SENSE.md](docs/PRODUCT_SENSE.md)
- [docs/RELIABILITY.md](docs/RELIABILITY.md)

For repository workflow and agent-focussed context, read [AGENTS.md](AGENTS.md).

## Repository knowledge

- [Documentation map](docs/knowledge/documentation-map.md) — RKE-managed reading order and relationship hub.
