# Quality Score

## Current assessment

This score is a blunt management tool, not a precise metric.

### Product clarity: 8/10

The user outcome, routing model, and configured-location boundary are explicit and backed by canonical docs.

### Contract certainty: 7/10

The backend contract is still reverse-engineered, but the critical current-state and routing paths are now fixture-backed and checked in.

### Runtime verification: 8/10

Pure logic, service handlers, config flow, sensor projection, mutation refresh, and Home Assistant lifecycle behaviour now have a sanitised regression harness and CI entrypoint.

### Repository hygiene: 8/10

The repo now has canonical docs, a contributor entrypoint, CI, a repeatable local test workflow, and a source-only tracked tree.

### Public readiness: 8/10

The repository is public-ready and maintainable, with remaining risk concentrated in the non-public backend contract rather than missing engineering foundations.

## Near-term target

Maintain confidence by:

1. periodically re-verifying the live backend contract and sanitising any new evidence
2. tightening packaging and release ergonomics as the public integration surface matures
