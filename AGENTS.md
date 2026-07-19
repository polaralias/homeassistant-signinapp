# AGENTS.md

## Purpose

This repository is being hardened from a working personal integration into a public, maintainable engineering artefact.

Agents working in this repo should optimise for:

1. Verified behaviour over plausible code.
2. Documentation that describes intended end state, not just current implementation.
3. Small, testable changes over broad rewrites.
4. Preserving evidence when reverse-engineering the Sign In App contract.

## Working rules

- Treat Home Assistant runtime behaviour as unverified until tested.
- Treat Sign In App backend behaviour as unstable unless captured in a dated verification artefact.
- Prefer adding or updating docs when a fact is discovered.
- Prefer fixtures and tests over prose when a contract can be mechanised.
- Do not hardcode secrets, tokens, companion codes, or personal data into the repo.
- Sanitise captured API artefacts before storing them.
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

- preserve verified behaviour as the primary acceptance bar
- keep canonical docs aligned with checked-in code and tests
- periodically re-verify the unstable backend contract and record sanitised evidence
- prefer bounded reliability, packaging, and publish-safety improvements over broad rewrites

## Shared Git Workflow

- work from a short-lived branch created from `main`
- do not commit directly to `main`
- use branch names prefixed with `feat/`, `fix/`, `docs/`, `chore/`, `refactor/`, or `test/`
- keep one logical change per branch and pull request
- open a pull request before merging to `main`, including for solo work
- prefer squash merge unless multiple commits carry durable review value
- delete the merged or closed feature branch after the work is finished; never delete `main`
- use tags in `vX.Y.Z` format for releases and do not move published tags
