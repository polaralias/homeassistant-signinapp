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
