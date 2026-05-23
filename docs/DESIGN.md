# Design

This repository does not own the Sign In App frontend.

Its design problem is integration design:

- how clearly Home Assistant models work-location attendance semantics
- how predictably the integration behaves under partial backend data
- how well documentation communicates the intended end state

Design priorities:

1. Make the product model obvious.
2. Make verified behavior distinguishable from inferred behavior.
3. Keep the contributor path short: understand, verify, change, test.

For design principles, see:

- [docs/design-docs/index.md](design-docs/index.md)
- [docs/design-docs/core-beliefs.md](design-docs/core-beliefs.md)
- [docs/design-docs/auth-model.md](design-docs/auth-model.md)
