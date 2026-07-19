# Reliability

## Reliability objective

The integration should produce the same sign-in, sign-out, and state-resolution decisions for the same observed inputs every time.

## Reliability principles

### Verified inputs beat folklore

Backend payload interpretation should be driven by captured evidence, not remembered behaviour.

### Cached context is a fallback, not a lie generator

Local session state exists to bridge backend ambiguity. It must never silently override clear live backend data.

When live backend state is explicit enough to identify the active or last-active work location, it should win over cached local session state.

A verified authoritative field such as `currentVisit.siteId` counts as explicit enough backend state for that purpose.

### Attendance routing precedence must be explicit

Attendance routing should prefer:

1. explicit action input
2. live backend state
3. cached local session state
4. configured user mappings
5. current Home Assistant location context when needed for location semantics

Concrete-target actions should fail if the selected configured target is temporarily unusable.

Fallback across different configured targets should happen only for hint-level actions and only by explicit policy.

Compatibility hints remain supported, but they are a non-primary surface and should not outgrow the concrete-target action model.

### Sign-in and sign-out are not symmetric

Sign-in should be explicit-first and simple.

Sign-out may require inference because the integration must safely recover which work location is currently active even when the backend response is partial.

Signed-out should be modelled as absence of an active work location, not as another configured target state.

This asymmetry means sign-in and sign-out should remain distinct verbs, not a flattened generic target-setting operation.

### Configured targets are the authority boundary

Configured available target states define the universe of valid action targets.

Runtime inference may narrow within that universe, but should not create targets outside it.

Configured target records should hold durable routing metadata only. Transient backend state belongs to runtime reads and caches, not durable configuration.

The minimum durable routing metadata set should be:

- stable backend identity
- user-facing label
- inclusion or enabled state
- coordinate-behaviour semantics
- any location-specific parameter required by those semantics

The current supported coordinate-behaviour set is:

- `device_tracker`
- `remote_zero`

No additional coordinate-behaviour modes should be implemented without a concrete scenario and explicit rule definition.

Runtime invalidity should be surfaced as runtime state, not silently converted into config mutation.

Unselected discovered work locations should be rediscovered when needed rather than persisted as non-authoritative shadow configuration.

### Canonical status classes must remain stable

The primary entity's core state should use stable canonical status classes.

Mutable work-location labels should influence presentation, not redefine the underlying state machine.

The desired canonical class set is:

- `signed_in`
- `signed_out`
- `unknown`

Work-location identity and label should be exposed through structured attributes, including last-active context when useful, rather than being encoded into the primary state string.

The primary entity attribute model should remain explicit and stable:

- `status_class`
- `active_work_location_id`
- `active_work_location_label`
- `last_active_work_location_id`
- `last_active_work_location_label`
- `status_reason`

`unknown` should mean the integration cannot currently assert a trustworthy attendance class, whether because the backend is unavailable or because the available data is semantically insufficient.

Last-active context is operational state, not just presentation. It supports safe sign-out inference and meaningful post-sign-out interpretation.

The initial operational `status_reason` categories should be:

- `backend_unavailable`
- `target_not_configured`
- `target_temporarily_unusable`
- `routing_ambiguous`
- `missing_location_context`
- `backend_contract_mismatch`

### Restart safety matters

The integration should still resolve correct state after Home Assistant restart, even when no mutation just occurred.

### Transport success is not product success

A `200` or `201` response is necessary but not sufficient. Reliability also requires that subsequent `config-v2` state matches the intended action.

### Drift should be visible, not silent

When backend-discovered routing hints drift from persisted routing semantics, the integration should preserve user-confirmed configuration by default.

Drift should be surfaced through an admin-facing issue and resolved through reconfiguration.

## Current reliability risks

- service behaviour depends on cached local session state
- the backend contract remains non-public and may drift without notice
- live contract re-verification still depends on disciplined local operator capture outside the checked-in harness
- the repeatable fixture suite covers pure logic, service-handler routing, sensor projection, focussed config-flow behaviour, and Home Assistant lifecycle behaviour, but it cannot guarantee future backend stability on its own
- full end-to-end Home Assistant platform loading on Windows currently relies on environment-level resolver and file-permission shims for `aiodns` selector-loop requirements and missing `os.fchmod`; for this repo they are treated as Home Assistant test-environment prerequisites, not integration-owned defects

## Desired end state

- observed payload variants represented in tests
- service actions verified by post-action state checks
- attendance-routing precedence represented in tests and docs
- sign-in and sign-out routing asymmetry represented in tests and docs
- signed-out absence and sign-out inference behaviour represented in tests and docs
- backend-versus-cache conflict resolution represented in tests and docs
- authoritative backend field handling represented in tests and docs
- configured-target authority represented in tests and docs
- durable-config versus transient-runtime-state boundaries represented in tests and docs
- rediscovery versus shadow-persistence of unselected work locations represented in tests and docs
- runtime invalidity versus durable inclusion state represented in tests and docs
- fail-hard versus hint-level fallback behaviour represented in tests and docs
- canonical status classes represented in tests and docs
- `unknown` reason handling represented in tests and docs
- active and last-active work-location attributes represented in tests and docs
- operational `status_reason` categories represented in tests and docs
- last-active operational behaviour represented in tests and docs
- drift detection, admin-facing surfacing, and reconfiguration review represented in tests and docs
- location-qualified status variants removed or deliberately constrained as presentation only
- restart and stale-cache behaviour tested explicitly
- contract drift detectable by failing tests or fixture review
