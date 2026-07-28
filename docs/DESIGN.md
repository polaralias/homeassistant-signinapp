---
type: "Design Concept"
title: "Design"
description: "Documents Design for the homeassistant-signinapp repository."
timestamp: 2026-07-28T21:55:36Z
authority: canonical
verification: untested
owner: polaralias
tags:
  - homeassistant-signinapp
  - design-concept
navigation:
  role: supporting
  order: 100
---
# Design

This repository does not own the Sign In App frontend.

Its design problem is integration design:

- how clearly Home Assistant models work-location attendance semantics
- how predictably the integration behaves under partial backend data
- how well documentation communicates the intended end state

Design priorities:

1. Make the product model obvious.
2. Make verified behaviour distinguishable from inferred behaviour.
3. Keep the contributor path short: understand, verify, change, test.

For design principles, see:

- [docs/design-docs/index.md](design-docs/index.md)
- [docs/design-docs/core-beliefs.md](design-docs/core-beliefs.md)
- [docs/design-docs/auth-model.md](design-docs/auth-model.md)

## Repository knowledge

- [Documentation map](knowledge/documentation-map.md) — RKE-managed reading order and relationship hub.
