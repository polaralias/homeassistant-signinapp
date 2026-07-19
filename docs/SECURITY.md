# Security

## Security posture

This project integrates with a non-public backend contract and handles bearer tokens for attendance actions. That makes secrecy and minimisation more important than in a normal public API integration.

## Security principles

### Never persist secrets in source control

Do not store:

- companion codes
- raw bearer tokens
- raw personal field data
- unsanitised captured responses

### Store only what the product needs

The product needs:

- access token in Home Assistant config entry
- configured work-location records containing stable backend identity and minimal routing metadata
- minimal cached session context for sign-out and state resolution

The product does not need:

- complete historic backend payload archives in the repo
- developer-only captured secrets

### Sanitise before documenting

Any verification artefact stored in the repo must redact:

- auth tokens
- personal email addresses
- opaque personal identifiers where not needed to explain behaviour

## Current concerns

- hardcoded client fingerprint headers may become a maintenance and detection liability
- reverse-engineered auth flows require disciplined evidence handling
- live contract re-verification still depends on local operator discipline outside the checked-in unit harness

## Desired end state

- token handling documented
- verification fixtures sanitised by default
- test harness uses redacted fixtures, not live secrets

## Local harness policy

- checked-in tests must run only on sanitised fixtures
- fixture names should describe behavioural shape, not real people or sites
- any fresh live capture must be sanitised before it is promoted into `tests/fixtures` or `docs/references`
- CI must not require live credentials or real Sign In App access
