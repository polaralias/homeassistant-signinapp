# Core Beliefs

## Belief 1: The repo should describe the intended system, not just the inherited one

Documentation should state desired behavior clearly enough that a maintainer can detect when the implementation falls short.

## Belief 2: Reverse-engineered contracts need evidence, not confidence

When the upstream API is private, every stable assumption should be backed by a dated observation, a fixture, or a test.

## Belief 3: State resolution is the core product risk

The hardest part of this integration is not sending HTTP requests. It is deciding what state the user is really in when backend data is incomplete, delayed, or drifted.

## Belief 4: Public-quality means verifiable

A public repo for hiring value should let a reviewer answer:

- what the product does
- how it works
- what is verified
- what is still risky

without guessing.
