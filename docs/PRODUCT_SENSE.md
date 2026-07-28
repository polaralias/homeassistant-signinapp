---
type: "Repository Knowledge"
title: "Product Sense"
description: "Documents Product Sense for the homeassistant-signinapp repository."
timestamp: 2026-07-28T21:55:36Z
authority: canonical
verification: untested
owner: polaralias
tags:
  - homeassistant-signinapp
  - repository-knowledge
navigation:
  role: supporting
  order: 100
---
# Product Sense

## Product outcome

The product is not "an API wrapper."

The product is:

- a Home Assistant integration whose purpose is reliable Sign In App attendance automation and state visibility

## User promise

A user should be able to:

1. connect their Sign In App account once
2. configure their supported work locations cleanly through the integration
3. have attendance routing operate across the work locations available to them
4. automate sign-in and sign-out confidently across those configured locations
5. trust the visible state in Home Assistant

The primary visible state should remain one user attendance entity, even when multiple work-location-backed action targets exist.

## Product boundaries

This repo owns:

- Home Assistant integration behaviour
- first-class setup and configuration flow
- translation of Home Assistant context into Sign In App requests
- translation of Sign In App responses into Home Assistant state

This repo does not own:

- Sign In App backend behaviour
- Sign In App companion frontend
- enterprise policy around attendance

## What good looks like

- sign-in and sign-out work with no guesswork
- the right work location can be targeted without the user hand-stitching raw backend site IDs
- state is correct after restarts
- ambiguous backend responses are handled explicitly
- setup is understandable without source-diving
- repo evidence supports public scrutiny

## Desired model

- open-ended support for work locations available to the user from Sign In App
- first-class dynamic configuration based on backend-discovered locations
- backend-discovered names offered as defaults, with user-overridable labels
- stable backend identities drive behaviour while mutable labels serve UX only

## Repository knowledge

- [Documentation map](knowledge/documentation-map.md) — RKE-managed reading order and relationship hub.
