---
type: "Security Boundary"
title: "Auth Model"
description: "Documents Auth Model for the homeassistant-signinapp repository."
timestamp: 2026-07-28T21:55:36Z
authority: canonical
verification: untested
owner: polaralias
tags:
  - homeassistant-signinapp
  - security-boundary
navigation:
  role: foundational
  order: 20
---
# Auth Model

## Desired end state

Authentication should behave as a narrow, explicit capability grant:

1. user provides a companion code
2. integration exchanges it for a bearer token
3. token is used only for the minimal mobile-backend operations the integration needs
4. token refresh behaviour is understood and documented

## Verified principles

- companion codes are normalised before exchange
- `POST /connect` returns a bearer token
- authenticated browser traffic uses that bearer token against `/api/mobile/*`
- `GET /reconnect` exists and returns a fresh token

## Known weaknesses

- repository code does not model reconnect explicitly
- request headers emulate a client fingerprint that can drift
- automatic `/reconnect` renewal remains unimplemented; 1.1.0 instead handles HTTP 401/403 through Home Assistant reauthentication with a fresh companion code for the same visitor
- synthetic transport and flow tests cover auth rejection, credential-safe logging, wrong-account rejection and preservation of routing during recovery

## Documentation rule

When auth behaviour is observed, document:

- the endpoint
- the minimal required request shape
- the minimal relied-on response shape
- the security implications

Do not document secrets themselves.

## Repository knowledge

- [Documentation map](../knowledge/documentation-map.md) — RKE-managed reading order and relationship hub.
