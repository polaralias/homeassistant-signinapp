# Observed API Contract 2026-05-16

## Scope

This file records observed backend behavior from a live authenticated session on 2026-05-16.

All secrets and personal data are sanitized.

## Observed endpoints

- `POST /api/mobile/connect`
- `GET /api/mobile/reconnect`
- `GET /api/mobile/config-v2`
- `GET /api/mobile/sites/{siteId}/today`
- `GET /api/mobile/upcoming`
- `GET /api/mobile/history`
- `POST /api/mobile/sign-in`
- `POST /api/mobile/sign-out`

## Minimal confirmed auth model

- `connect` accepts a normalized companion code
- authenticated requests use `Authorization: Bearer <token>`
- `reconnect` returns a fresh token

## Minimal confirmed sign-in model

- remote sign-in works with `siteId=<remote>` and zeroed coordinates
- office sign-in works with `siteId=<office>` and office geofence coordinates
- successful sign-in returned HTTP `201` in the verified session

## Minimal confirmed sign-out model

- office sign-out worked with office geofence coordinates
- remote sign-out worked with zeroed coordinates
- successful sign-out returned HTTP `200` with `{ "success": true }` in the verified session

## Minimal confirmed state model

Observed `config-v2` fields relevant to this integration included:

- `returningVisitor.status`
- `returningVisitor.lastIn`
- `returningVisitor.lastOut`
- `returningVisitor.name`
- `returningVisitor.groupId`
- `currentVisit.siteId`
- `sites[].id`
- `sites[].name`
- `sites[].type`
- `sites[].location.position.lat`
- `sites[].location.position.lng`
- `sites[].location.radius`

## Important contract note

`currentVisit.siteId` is a verified live field and must be treated as part of the current-site resolution contract.

It should also be treated as a verified authoritative backend identity field for backend-versus-cache conflict resolution.

## Drift note

The live browser app used `x-app-version: Web companion app/3.21.1+302188`, while repository code still hardcodes an older version string.
