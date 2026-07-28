---
type: "Product Contract"
title: "API Contract Discovery 2026-05-16"
description: "Documents API Contract Discovery 2026-05-16 for the homeassistant-signinapp repository."
timestamp: 2026-07-28T21:55:36Z
authority: canonical
verification: untested
owner: polaralias
tags:
  - homeassistant-signinapp
  - product-contract
navigation:
  role: foundational
  order: 20
---
# API Contract Discovery 2026-05-16

## Outcome

A live verification pass was completed against the Sign In App companion app and backend.

## What was confirmed

- `POST /connect`
- `GET /reconnect`
- `GET /config-v2`
- `POST /sign-in`
- `POST /sign-out`
- remote sign-in with zeroed coordinates
- office sign-out with office geofence coordinates

## What changed in our understanding

- live `config-v2` uses `currentVisit.siteId`
- current code does not resolve current site from that field
- hardcoded `x-app-version` in the repo is stale

## Evidence

- [observed-api-contract-2026-05-16.md](../../references/observed-api-contract-2026-05-16.md)
- [codebase-survey-2026-05-16.md](../../references/codebase-survey-2026-05-16.md)

## Follow-on action

This discovery pass is complete only as evidence gathering. The next phase is harness construction and targeted correctness fixes.

## Repository knowledge

- [Documentation map](../../knowledge/documentation-map.md) — RKE-managed reading order and relationship hub.
