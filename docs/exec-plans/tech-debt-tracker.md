---
type: "Delivery Plan"
title: "Tech Debt Tracker"
description: "Documents Tech Debt Tracker for the homeassistant-signinapp repository."
timestamp: 2026-07-28T21:55:36Z
authority: canonical
verification: untested
owner: polaralias
tags:
  - homeassistant-signinapp
  - delivery-plan
navigation:
  role: supporting
  order: 100
---
# Tech Debt Tracker

## Site form localisation

Resolved in this release: each site now uses a repeated `site` step with fixed `enabled`, `label`, and `distance` keys. Its friendly name and review progress appear in description placeholders. The initial `sites` step selects the person tracker. Dynamic site IDs are kept in internal flow state and persisted routing records.

Verification on 2026-10-08: config-flow tests cover stable schema keys, office and remote location handling, label overrides, excluded sites, correction after excluding every site, no available sites, saved reconfiguration defaults, missing sites, token preservation, and a single update/reload after the final step. Actual Home Assistant translation-cache tests verify the new labels for `en` and `en-GB`. Live frontend rendering remains unverified.

Historical debt items from the harness tranche have been closed through checked-in tests, CI, docs, and config-model migration support.

## Repository knowledge

- [Documentation map](../knowledge/documentation-map.md) â€” RKE-managed reading order and relationship hub.

## Reliability fixes in 1.1.0

Explicit sign-out targets must be configured and enabled; invalid explicit IDs cannot fall back to a cached site. Removed or disabled cached and backend targets cannot authorize an attendance mutation. Coordinates must be finite and within geographic ranges, with non-negative accuracy.

Transport responses reject authentication errors, invalid JSON shapes and explicit success=false. A mutation is sent once, then up to three config-v2 reads check the expected status (and site for sign-in). Local session state is committed only after confirmation. An unconfirmed request may have reached the backend: check attendance before retrying. There is no automatic mutation retry.

HTTP 401/403 starts Home Assistant reauthentication. A fresh companion code must identify the same visitor; successful recovery preserves routing and config entry identity. Unknown backend statuses project to canonical unknown. Request logs contain method, endpoint and HTTP status, never credentials or response bodies.

Regression tests use synthetic responses and do not change real attendance. Linux CI covers HA 2025.1.4/Python 3.12 and HA 2026.10.4/Python 3.14. The external backend contract still requires live operator verification.
