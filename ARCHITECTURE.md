# Architecture

## System summary

This repository contains a Home Assistant custom integration whose product purpose is reliable Sign In App attendance automation and state visibility.

The integration does five things:

1. Exchanges a companion code for a bearer token.
2. Fetches account and work-location configuration from the Sign In App mobile backend.
3. Lets the user configure work locations and attendance routing through Home Assistant config flow.
4. Exposes Home Assistant services to sign in and sign out across those configured locations.
5. Exposes a single Home Assistant entity representing the user's current attendance state.

These actions should remain distinct verbs, not collapse into a generic attendance-target setter.

## Main components

### Home Assistant integration shell

Files:

- [custom_components/signinapp/__init__.py](custom_components/signinapp/__init__.py)
- [custom_components/signinapp/manifest.json](custom_components/signinapp/manifest.json)

Responsibilities:

- service registration
- config entry setup and teardown
- persisted session context storage
- platform registration
- single primary user attendance entity

### Config flow

File:

- [custom_components/signinapp/config_flow.py](custom_components/signinapp/config_flow.py)

Responsibilities:

- companion code entry
- token acquisition
- dynamic work-location discovery from backend data
- backend-discovered work-location names offered as initial config values
- user-overridable work-location labels
- stable backend work-location identities preserved for routing and entity identity
- durable routing metadata persisted per configured work location
- backend-discovered routing hints confirmed during config flow before becoming durable configuration
- explicit inclusion or exclusion of discovered work locations before they become available target states
- configuration of current attendance routing behaviour
- person entity selection

Unselected discovered work locations should be rediscovered on demand rather than persisted as shadow durable configuration.

Persisted routing metadata should stay intentionally small and durable:

- stable backend work-location identity
- user-facing label
- inclusion or enabled state
- coordinate-behaviour semantics
- any location-specific parameter required by those semantics

Presentation grouping for automation UX should be derived from persisted routing metadata rather than stored as separate durable configuration unless explicitly needed later.

If backend-discovered routing hints later drift from persisted configuration, the integration should preserve user-confirmed configuration by default, raise an admin-facing issue, and resolve the difference through reconfiguration rather than silent mutation.

### API client

File:

- [custom_components/signinapp/api.py](custom_components/signinapp/api.py)

Responsibilities:

- request construction
- auth header handling
- connect, config fetch, sign-in, sign-out requests

### Domain logic

File:

- [custom_components/signinapp/logic.py](custom_components/signinapp/logic.py)

Responsibilities:

- normalise inputs
- resolve work-location type
- resolve current work location from backend payloads
- execute attendance routing decisions for service actions and state resolution
- resolve sign-out context
- resolve sensor state

This is the integration's real decision layer and should become the first-class verification target.

Attendance routing should use these inputs in precedence order:

1. explicit action input
2. live backend state
3. cached local session state
4. configured user mappings
5. current Home Assistant location context when needed to supply location semantics

If live backend state and cached local session state disagree, explicit live backend state should win.

Explicit backend state means stable backend work-location identity surfaced through a verified authoritative field such as `currentVisit.siteId`.

Attendance routing is intentionally asymmetric:

- sign-in should be explicit-first
- sign-out may infer the active work location from live backend state and cached local session state when explicit input is absent
- signed-out should be treated as absence of an active work location, while sign-out inference recovers the previously active signed-in work location

This asymmetry is one reason sign-in and sign-out remain distinct product verbs.

Explicit action input should evolve towards concrete work-location identity.

Routing-mode hints such as today's office or remote model should be treated as a compatibility layer rather than the final product surface.

The supported transition action surface should be prioritised in this order:

1. explicit concrete work-location identity
2. sign-out with no explicit target using inference rules
3. routing-hint compatibility input such as office-like or remote-like behaviour

Concrete-target actions should fail if the chosen configured target is temporarily unusable.

Cross-target fallback should be reserved for hint-level actions and explicit routing policy.

Mutable user labels should affect UX only.

Routing and entity identity should use stable backend work-location identity.

### Sensor surface

File:

- [custom_components/signinapp/sensor.py](custom_components/signinapp/sensor.py)

Responsibilities:

- poll `config-v2`
- project backend state into the single primary user attendance entity
- expose canonical status classes as the core state vocabulary
- expose work-location identity and label as structured metadata or presentation
- expose active and last-active work-location identity and label through structured attributes when available
- expose operational reason metadata when the canonical class is `unknown` or when a configured target is temporarily unusable

Last-active context should be treated as operational state that supports sign-out inference and post-sign-out interpretation.

The desired canonical status class set is:

- `signed_in`
- `signed_out`
- `unknown`

`unknown` should cover both transport unavailability and unresolved semantic ambiguity, with reason exposed through attributes or diagnostics rather than new canonical classes.

The primary entity attribute model should include:

- `status_class`
- `active_work_location_id`
- `active_work_location_label`
- `last_active_work_location_id`
- `last_active_work_location_label`
- `status_reason`

The initial operational `status_reason` set should include:

- `backend_unavailable`
- `target_not_configured`
- `target_temporarily_unusable`
- `routing_ambiguous`
- `missing_location_context`
- `backend_contract_mismatch`

Configured work locations should appear as available target states for actions, not as separate primary attendance entities.

The configured set of available target states should be authoritative.

Attendance routing may apply validity and inference rules at action time, but only within the configured set.

Runtime observations may surface temporary invalidity, but should not silently mutate durable inclusion state.

## Runtime model

The runtime model is:

1. Config flow stores token and selected backend site IDs for the configured work locations.
2. Config flow stores durable routing metadata for those configured work locations.
3. Unselected discovered work locations are not part of durable configuration.
4. Integration should treat backend work-location identity as stable and user labels as mutable presentation.
5. Integration stores API client and cached session context in `hass.data`.
6. Service calls mutate remote state through Sign In App.
7. Sensor polling reads remote state from `config-v2`.
8. Local cached session context fills gaps when backend responses are ambiguous.

The entity model should remain:

- one primary user attendance entity
- multiple available target states for actions
- canonical status classes in the primary state machine

Action-time behaviour should narrow from configured targets, not create new ones outside configuration.

## Architectural risks

### Desired model

Desired end state:

- config flow iterates across all available backend work locations
- config flow seeds names from backend-discovered locations but allows user overrides
- config flow presents backend-discovered routing hints for confirmation before persistence
- config flow requires explicit inclusion before a discovered work location becomes an available target state
- config persists durable routing metadata per configured work location
- configuration is expressed as user routing behaviour, not just two fixed mappings
- drift between persisted configuration and newly discovered backend hints raises an admin-facing issue and is resolved through reconfiguration
- canonical docs describe the end state, while references and plans capture current-state evidence
### Reverse-engineered backend contract

The integration depends on a non-public API contract.

Desired end state:

- observed contract documented
- observed contract represented in fixtures
- logic tested against known response shapes

### Cached session dependence

The integration uses `current_session` and `last_session` to recover context the backend may not return consistently.

Desired end state:

- clear rules for when cached session data is authoritative
- clear precedence rules for attendance-routing inputs
- explicit documentation and tests for sign-in versus sign-out routing asymmetry
- tests for restart, stale cache, and missing current-work-location fields

### Boundary mismatch

The current integration mixes:

- Home Assistant lifecycle code
- backend transport concerns
- contract interpretation rules

Desired end state:

- domain rules verified independently
- transport assumptions documented explicitly
- runtime wiring covered by focussed integration tests
