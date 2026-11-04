---
type: "Product Contract"
title: "Observed attendance history contract 2026-11-04"
description: "Sanitised observations of the companion account history endpoint."
timestamp: 2026-11-04T19:00:00Z
authority: canonical
verification: tested
owner: polaralias
tags: [signinapp, history, api-contract]
---
# Observed attendance history contract

Read-only verification on 4 November 2026 used an already authorised companion
account. No sign-in or sign-out was performed. The API is non-public and may change.
Raw captures remain outside this repository; tests use synthetic records.

- `GET /api/mobile/history` accepts `dateFrom` and `dateTo` as ISO dates with the
  integration's bearer credential and `x-timezone` header.
- Missing dates or equal bounds returned HTTP 422. A valid multi-day request and
  one-day request returned HTTP 200 with a root JSON list of session dictionaries.
- A one-day query included an overnight session starting the preceding day, so
  the observed filter includes overlapping sessions. The client still clips every
  interval to requested reporting boundaries and deduplicates chunk overlaps.
- Sessions included `id`, `siteId`, `siteName`, `inTimestamp`, `inDateTime`,
  `outTimestamp`, `outDateTime`, `activityStatusChanges` and `timezone`.
- Epoch timestamps were in seconds and agreed with UTC ISO timestamp fields.
- Activity changes included `changedAt` and a `status` dictionary with stable
  `id`, `name`, boolean `isWorking` and archival metadata.
- `config-v2` exposed `returningVisitor.canViewSignInHistory` and current activity
  definitions. No precomputed daily/weekly totals or quota were found in these
  responses. Quotas are therefore explicit integration configuration.

Captured sessions were closed. Null/zero out timestamps and an omitted active
session are defensive code paths covered by synthetic tests, not a verified open
session wire contract. Working classification is left unavailable when the API
does not supply it. History 403 versus 401 handling is a tested permission boundary,
not an observed permission denial on the authorised live account.
