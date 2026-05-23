# AGENTS.md

## Purpose

This repository is being hardened from a working personal integration into a public, maintainable engineering artifact.

Agents working in this repo should optimize for:

1. Verified behavior over plausible code.
2. Documentation that describes intended end state, not just current implementation.
3. Small, testable changes over broad rewrites.
4. Preserving evidence when reverse-engineering the Sign In App contract.

## Working rules

- Treat Home Assistant runtime behavior as unverified until tested.
- Treat Sign In App backend behavior as unstable unless captured in a dated verification artifact.
- Prefer adding or updating docs when a fact is discovered.
- Prefer fixtures and tests over prose when a contract can be mechanized.
- Do not hardcode secrets, tokens, companion codes, or personal data into the repo.
- Sanitize captured API artifacts before storing them.
- Keep README concise and point readers to the structured docs set.

## Documentation map

- [README.md](README.md)
- [GLOSSARY.md](GLOSSARY.md)
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [docs/DESIGN.md](docs/DESIGN.md)
- [docs/PLANS.md](docs/PLANS.md)
- [docs/PRODUCT_SENSE.md](docs/PRODUCT_SENSE.md)
- [docs/QUALITY_SCORE.md](docs/QUALITY_SCORE.md)
- [docs/RELIABILITY.md](docs/RELIABILITY.md)
- [docs/SECURITY.md](docs/SECURITY.md)

## Current strategic focus

The repository is now in public-release maintenance mode:

- preserve verified behavior as the primary acceptance bar
- keep canonical docs aligned with checked-in code and tests
- periodically re-verify the unstable backend contract and record sanitized evidence
- prefer bounded reliability, packaging, and publish-safety improvements over broad rewrites
