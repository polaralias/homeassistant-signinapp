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

## Dynamic site form labels

Audit on 2026-10-08: `translations/en.json` supplies the fixed companion-code and person-tracker labels, repair strings, and sensor state strings. Automated Home Assistant translation-cache tests verify the fixed labels for `en` and `en-GB`.

The site form generates fields such as `site_100_enabled`, `site_100_label`, and `site_100_distance`. Those backend-dependent keys have no static translations and the frontend falls back to their raw names. Adding an `en-GB.json` file cannot solve this.

A follow-up should present sites through repeated steps with stable translatable field keys and a site-name description placeholder. Preserve configured-location IDs, inclusion, label overrides, distance semantics, reconfiguration defaults, missing-site handling, and error recovery. This flow redesign is pending; the audit does not claim the dynamic labels are fixed.

Historical debt items from the harness tranche have been closed through checked-in tests, CI, docs, and config-model migration support.

## Repository knowledge

- [Documentation map](../knowledge/documentation-map.md) — RKE-managed reading order and relationship hub.
